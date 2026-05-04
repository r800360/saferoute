from __future__ import annotations

from pathlib import Path
from typing import Protocol

from autopass_gen.agents.execution import ExecutionAgent
from autopass_gen.agents.perception import PerceptionMapTools
from autopass_gen.agents.policy import AggressivePolicy, NoPassPolicy, UrgencyAwarePassingPolicy
from autopass_gen.agents.urgency import RequestUrgencyInterpreter
from autopass_gen.core.schema import Decision, EgoState, RolloutMetrics, ScenarioSpec
from autopass_gen.evaluation.evaluator import Evaluator


class Policy(Protocol):
    def decide(self, state): ...


def make_policy(name: str) -> Policy:
    if name == "autopass":
        return UrgencyAwarePassingPolicy()
    if name == "no_pass":
        return NoPassPolicy()
    if name == "aggressive":
        return AggressivePolicy()
    raise ValueError(f"Unknown policy: {name}")


class RolloutRunner:
    def __init__(
        self, out_dir: str | Path = "runs/latest", dt_s: float = 1.0, max_steps: int = 180
    ):
        self.interpreter = RequestUrgencyInterpreter()
        self.perception = PerceptionMapTools(seed=0)
        self.execution = ExecutionAgent()
        self.evaluator = Evaluator(out_dir)
        self.dt_s = dt_s
        self.max_steps = max_steps

    def run(self, spec: ScenarioSpec, policy_name: str = "autopass") -> RolloutMetrics:
        urgency = self.interpreter.interpret(spec.request, spec.route)
        ego = EgoState(x_m=0.0, speed_mps=spec.ego.speed_mps, lane="current")
        policy = make_policy(policy_name)
        trace = []
        pass_attempts = 0
        unsafe_passes = 0

        for step in range(self.max_steps):
            t_s = step * self.dt_s
            state = self.perception.estimate(spec, urgency, ego, t_s)
            state = policy.decide(state)
            if state.decision == Decision.PASS:
                pass_attempts += 1
                if not state.critic_approved:
                    unsafe_passes += 1
            trace.append(state)
            ego = self.execution.step(spec, state, self.dt_s)
            if ego.x_m >= spec.route.length_m:
                break
            lead_collision = state.lead_distance_m <= 1.5 and ego.lane == "current"
            oncoming_collision = state.oncoming_distance_m <= 0 and ego.lane == "passing"
            if lead_collision or oncoming_collision:
                break

        collision = self.evaluator.collision_from_trace(trace)
        route_completed = ego.x_m >= spec.route.length_m
        min_ttc = self.evaluator.min_ttc(trace)
        failure = self.evaluator.classify_failure(spec, trace, collision, route_completed, min_ttc)
        trace_path = self.evaluator.save_trace(spec.scenario_id, policy_name, trace)
        return RolloutMetrics(
            scenario_id=spec.scenario_id,
            policy_name=policy_name,
            collision=collision,
            route_completed=route_completed,
            time_to_goal_s=trace[-1].t_s if trace else 0.0,
            pass_attempts=pass_attempts,
            unsafe_passes=unsafe_passes,
            min_ttc_s=min_ttc,
            generated_failure=failure.value != "none",
            failure_type=failure,
            final_decision=trace[-1].decision or Decision.WAIT,
            trace_path=trace_path,
        )
