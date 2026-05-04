from autopass_gen.agents.urgency import RequestUrgencyInterpreter
from autopass_gen.core.schema import RequestSpec, RouteSpec
from autopass_gen.core.generator import ScenarioGenerator
from autopass_gen.sim.rollout import RolloutRunner


def test_urgency_interpreter_high():
    ctx = RequestUrgencyInterpreter().interpret(
        RequestSpec(text="I am late and need to arrive in 5 minutes", deadline_min=5),
        RouteSpec(),
    )
    assert ctx.urgency_level == "high"
    assert ctx.delay_cost > 1


def test_generator_and_rollout(tmp_path):
    spec = ScenarioGenerator(seed=1).sample(1)[0]
    metrics = RolloutRunner(out_dir=tmp_path).run(spec, policy_name="autopass")
    assert metrics.scenario_id == spec.scenario_id
    assert metrics.trace_path
