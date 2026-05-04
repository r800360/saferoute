from __future__ import annotations

from autopass_gen.core.schema import Decision, EgoState, PassState, ScenarioSpec


class ExecutionAgent:
    """Converts decisions to a simple kinematic update. CARLA executor can mirror this interface."""

    def step(self, spec: ScenarioSpec, state: PassState, dt_s: float = 1.0) -> EgoState:
        ego = state.ego.model_copy(deep=True)

        if state.decision == Decision.PASS:
            ego.lane = "passing"
            ego.speed_mps = min(
                spec.ego.desired_speed_mps + 1.5,
                ego.speed_mps + 1.2,
            )

        elif state.decision == Decision.REPLAN:
            ego.lane = "current"
            # ego.speed_mps = max(4.0, ego.speed_mps - 0.5)
            # Replan should be conservative: slow down and create space.
            if state.lead_distance_m < 20.0:
                ego.speed_mps = max(0.0, min(ego.speed_mps - 2.0, state.lead_speed_mps))
            else:
                ego.speed_mps = max(4.0, ego.speed_mps - 0.8)

        else:
            ego.lane = "current"

            # Simple adaptive cruise control for the lightweight simulator.
            # WAIT should mean "follow safely," not "keep driving into the lead car."
            emergency_gap_m = 7.0
            desired_gap_m = 22.0
            follow_gap_m = 38.0

            if state.lead_distance_m < emergency_gap_m:
                # Hard brake if very close.
                ego.speed_mps = max(
                    0.0,
                    min(ego.speed_mps - 3.0, state.lead_speed_mps - 2.0),
                )
            elif state.lead_distance_m < desired_gap_m:
                # Back off until the gap recovers.
                ego.speed_mps = max(
                    1.0,
                    min(ego.speed_mps - 1.0, state.lead_speed_mps - 0.5),
                )
            elif state.lead_distance_m < follow_gap_m:
                # Match the lead vehicle.
                ego.speed_mps = max(
                    2.0,
                    min(ego.speed_mps, state.lead_speed_mps),
                )
            else:
                # Free-road acceleration.
                ego.speed_mps = min(
                    spec.ego.desired_speed_mps,
                    ego.speed_mps + 0.4,
                )

        ego.x_m += ego.speed_mps * dt_s
        return ego
