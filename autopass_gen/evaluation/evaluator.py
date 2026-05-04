from __future__ import annotations

from pathlib import Path

import pandas as pd

from autopass_gen.core.io import save_json
from autopass_gen.core.schema import Decision, FailureType, PassState, RolloutMetrics, ScenarioSpec


class Evaluator:
    def __init__(self, out_dir: str | Path = "runs/latest"):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def classify_failure(
        self,
        spec: ScenarioSpec,
        trace: list[PassState],
        collision: bool,
        route_completed: bool,
        min_ttc_s: float,
    ) -> FailureType:
        if not trace:
            return FailureType.NONE

        final = trace[-1]

        pass_attempted = any(s.decision == Decision.PASS for s in trace)
        unsafe_pass_attempted = any(
            s.decision == Decision.PASS and not s.critic_approved for s in trace
        )

        # A "safe opportunity" should be detected over the whole rollout,
        # not only at the final timestep.
        safe_window_seen = any(
            s.oncoming_distance_m > 100.0
            and s.rear_distance_m > 25.0
            and s.visibility_m > 70.0
            and s.lead_distance_m > 8.0
            for s in trace
        )

        # Deadline is only meaningful as a failure if the route was not completed
        # or was completed after the request deadline.
        deadline_missed = final.t_s / 60.0 > spec.request.deadline_min

        if collision:
            return FailureType.COLLISION

        if pass_attempted and (min_ttc_s < 2.0 or unsafe_pass_attempted):
            return FailureType.UNSAFE_PASS

        if (
            spec.sensor.mode != "privileged"
            and final.visibility_m < 45.0
            and final.risk > 0.5
            and not route_completed
        ):
            return FailureType.SENSOR_MODE_FAILURE

        if not route_completed and not pass_attempted:
            return FailureType.OVER_CONSERVATIVE_DELAY

        if not route_completed and safe_window_seen and final.urgency in ["medium", "high"]:
            return FailureType.MISSED_SAFE_PASS

        if deadline_missed and not pass_attempted and final.urgency in ["medium", "high"]:
            return FailureType.OVER_CONSERVATIVE_DELAY

        return FailureType.NONE

    def save_trace(self, scenario_id: str, policy_name: str, trace: list[PassState]) -> str:
        path = self.out_dir / "traces" / f"{scenario_id}_{policy_name}.json"
        save_json([s.model_dump(mode="json") for s in trace], path)
        return str(path)

    def save_metrics_csv(
        self, metrics: list[RolloutMetrics], filename: str = "metrics.csv"
    ) -> Path:
        path = self.out_dir / filename
        pd.DataFrame([m.model_dump(mode="json") for m in metrics]).to_csv(path, index=False)
        return path

    @staticmethod
    def collision_from_trace(trace: list[PassState]) -> bool:
        for s in trace:
            lead_collision = s.lead_distance_m <= 1.5 and s.ego.lane == "current"

            oncoming_collision = s.oncoming_distance_m <= 0.0 and s.ego.lane == "passing"

            if lead_collision or oncoming_collision:
                return True

        return False

    @staticmethod
    def min_ttc(trace: list[PassState]) -> float:
        vals: list[float] = []

        for s in trace:
            if s.ego.lane != "passing":
                continue

            closing_speed = s.ego.speed_mps + s.oncoming_speed_mps

            if closing_speed <= 0.0:
                continue

            vals.append(max(0.0, s.oncoming_distance_m / closing_speed))

        return min(vals) if vals else float("inf")
