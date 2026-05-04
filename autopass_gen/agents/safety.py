from __future__ import annotations

from dataclasses import dataclass
import math

from autopass_gen.core.schema import PassState


@dataclass
class SafetyConfig:
    vehicle_length_m: float = 4.8
    pass_distance_buffer_m: float = 12.0
    rear_min_ttc_s: float = 3.0
    oncoming_min_ttc_s: float = 4.0
    min_visibility_m: float = 65.0
    max_allowed_risk: float = 0.65


class SafetyChecker:
    def __init__(self, cfg: SafetyConfig | None = None):
        self.cfg = cfg or SafetyConfig()

    def evaluate_pass(self, state: PassState) -> tuple[bool, float, str, float]:
        t_pass = self.estimate_passing_time(state)
        required_gap = (
            state.ego.speed_mps * t_pass + 0.5 * 1.0 * t_pass**2 + self.cfg.pass_distance_buffer_m
        )
        oncoming_ttc = self.ttc(
            state.oncoming_distance_m, state.ego.speed_mps + state.oncoming_speed_mps
        )
        rear_closing = max(0.1, state.rear_speed_mps - state.ego.speed_mps)
        rear_ttc = self.ttc(state.rear_distance_m, rear_closing)

        violations = []
        if state.visibility_m < self.cfg.min_visibility_m:
            violations.append(f"low visibility {state.visibility_m:.1f}m")
        if state.oncoming_distance_m < required_gap:
            violations.append(
                f"oncoming gap {state.oncoming_distance_m:.1f}m < required {required_gap:.1f}m"
            )
        if oncoming_ttc < self.cfg.oncoming_min_ttc_s:
            violations.append(f"oncoming TTC {oncoming_ttc:.1f}s")
        if rear_ttc < self.cfg.rear_min_ttc_s:
            violations.append(f"rear TTC {rear_ttc:.1f}s")
        if state.lead_distance_m < 6.0:
            violations.append("too close to lead vehicle")

        risk = self.risk_score(state, oncoming_ttc, rear_ttc, required_gap)
        approved = not violations and risk <= self.cfg.max_allowed_risk
        reason = "approved" if approved else "; ".join(violations) or f"risk {risk:.2f} too high"
        return approved, risk, reason, min(oncoming_ttc, rear_ttc)

    def estimate_passing_time(self, state: PassState) -> float:
        relative = max(1.0, state.ego.speed_mps - state.lead_speed_mps)
        distance_to_clear = (
            state.lead_distance_m
            + 2.0 * self.cfg.vehicle_length_m
            + self.cfg.pass_distance_buffer_m
        )
        return max(2.5, distance_to_clear / relative)

    @staticmethod
    def ttc(distance: float, closing_speed: float) -> float:
        if closing_speed <= 0:
            return math.inf
        return max(0.0, distance / closing_speed)

    def risk_score(
        self, state: PassState, oncoming_ttc: float, rear_ttc: float, required_gap: float
    ) -> float:
        gap_risk = max(0.0, 1.0 - state.oncoming_distance_m / max(required_gap, 1.0))
        vis_risk = max(0.0, 1.0 - state.visibility_m / self.cfg.min_visibility_m)
        rear_risk = max(0.0, 1.0 - rear_ttc / self.cfg.rear_min_ttc_s)
        ttc_risk = max(0.0, 1.0 - oncoming_ttc / self.cfg.oncoming_min_ttc_s)
        return min(1.0, 0.35 * gap_risk + 0.25 * vis_risk + 0.2 * rear_risk + 0.2 * ttc_risk)
