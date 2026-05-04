from __future__ import annotations

from autopass_gen.agents.safety import SafetyChecker
from autopass_gen.core.schema import Decision, PassState


class UrgencyAwarePassingPolicy:
    def __init__(self, safety: SafetyChecker | None = None):
        self.safety = safety or SafetyChecker()

    def decide(self, state: PassState) -> PassState:
        blocked = state.lead_distance_m < 45.0 and state.lead_speed_mps < 0.85 * state.ego.speed_mps
        if not blocked:
            state.decision = Decision.WAIT
            state.reason = "not blocked by a slow lead vehicle"
            return state

        approved, risk, reason, _ = self.safety.evaluate_pass(state)
        state.risk = risk
        state.critic_approved = approved

        urgency_bias = {"low": 0.10, "medium": 0.0, "high": -0.08}[state.urgency]
        pass_consideration_threshold = 0.48 + urgency_bias
        progress_need = self._progress_need(state)

        if approved and risk <= pass_consideration_threshold and progress_need > 0.25:
            state.decision = Decision.PASS
            state.reason = f"pass approved; progress_need={progress_need:.2f}; risk={risk:.2f}"
        elif (
            state.urgency == "high" and not approved and "visibility" not in reason and risk < 0.75
        ):
            state.decision = Decision.REPLAN
            state.reason = f"high urgency but pass rejected, so replan; {reason}"
        else:
            state.decision = Decision.WAIT
            state.reason = f"wait; {reason}; progress_need={progress_need:.2f}; risk={risk:.2f}"
        return state

    @staticmethod
    def _progress_need(state: PassState) -> float:
        # A lightweight proxy: low deadline + slow lead creates high need to pass.
        deadline_pressure = max(0.0, min(1.0, (15.0 - state.deadline_min) / 12.0))
        speed_loss = max(
            0.0,
            min(1.0, (state.ego.speed_mps - state.lead_speed_mps) / max(state.ego.speed_mps, 1.0)),
        )
        return 0.55 * deadline_pressure + 0.45 * speed_loss


class NoPassPolicy:
    name = "no_pass"

    def decide(self, state: PassState) -> PassState:
        state.decision = Decision.WAIT
        state.reason = "baseline never attempts passing"
        return state


class AggressivePolicy:
    name = "aggressive"

    def __init__(self, safety: SafetyChecker | None = None):
        self.safety = safety or SafetyChecker()

    def decide(self, state: PassState) -> PassState:
        approved, risk, reason, _ = self.safety.evaluate_pass(state)
        state.critic_approved = approved
        state.risk = risk
        # This baseline intentionally ignores some rejections under urgency for comparison.
        if approved or (
            state.urgency == "high" and state.visibility_m > 35 and state.oncoming_distance_m > 35
        ):
            state.decision = Decision.PASS
            state.reason = f"aggressive pass; safety says: {reason}"
        else:
            state.decision = Decision.WAIT
            state.reason = f"aggressive wait; {reason}"
        return state
