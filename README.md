# AutoPass-Gen Initial Prototype

AutoPass-Gen is an initial CSE 252D Advanced Computer Vision prototype for generation-driven evaluation of urgency-aware passing decisions in CARLA.

This repository implements the full design-document loop in a lightweight, testable way:

1. `ScenarioSpec` DSL for route, request, traffic, occlusion, weather, and sensors
2. scenario generator and failure mutator
3. request/urgency interpreter
4. perception/map tools with privileged or noisy sensor state
5. urgency-aware passing policy
6. safety checker using TTC, rear-gap, oncoming-gap, and visibility constraints
7. execution layer with simple kinematic rollout
8. evaluator with metrics, failure taxonomy, traces, and plots
9. CARLA adapter stub for replacing the kinematic simulator with real CARLA calls

## Quick start

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -e .
python -m autopass_gen.cli demo --out-dir runs/demo
```

Outputs:

- `runs/demo/metrics.csv`
- `runs/demo/traces/*.json`
- `runs/demo/figures/summary_by_policy.csv`
- `runs/demo/figures/failure_rates.png`
- `runs/demo/figures/efficiency_passes.png`

## Useful commands

```bash
# Generate scenarios
python -m autopass_gen.cli generate --n 50 --out-dir configs/generated --seed 0

# Run three policies on the generated scenarios
python -m autopass_gen.cli run --scenario-dir configs/generated --out-dir runs/batch \
  --policies autopass,no_pass,aggressive

# Run tests
pytest -q
```

## Repository layout

```text
autopass_gen/
  core/
    schema.py        # ScenarioSpec, PassState, metrics, decisions
    generator.py     # sampling and mutation of scenarios
    io.py            # JSON load/save helpers
  agents/
    urgency.py       # request/deadline to urgency and delay cost
    perception.py    # privileged/noisy RGB-depth style estimates
    safety.py        # TTC, gap, visibility checks
    policy.py        # autopass/no-pass/aggressive policies
    execution.py     # decision to kinematic control update
  sim/
    rollout.py       # closed-loop rollout runner
  evaluation/
    evaluator.py     # metrics, failure taxonomy, trace saving
  carla/
    adapter.py       # placeholder boundary for real CARLA integration
  utils/
    plots.py         # summary CSV and figures
configs/
  example_scenario.json
scripts/
  run_demo.py
tests/
  test_core.py
```

## What is implemented versus what remains

Implemented now:

- Full closed-loop architecture without requiring CARLA installation
- Scenario DSL matching the paper design
- Auditable traces explaining pass/wait/replan decisions
- Three policy comparisons: AutoPass, no-pass, aggressive
- Initial quantitative metrics and failure taxonomy

Next CARLA integration steps:

1. Implement `CarlaAdapter.connect()` with the local CARLA Python API.
2. Implement `instantiate(spec)` to load the town, spawn ego/lead/rear/oncoming actors, set weather, and attach sensors.
3. Replace `PerceptionMapTools.estimate()` with CARLA actor state first, then RGB/depth estimates for selected quantities.
4. Replace `ExecutionAgent.step()` with BasicAgent or local planner control commands.
5. Record videos and align each video with the JSON trace.

## Design principle

The research contribution is not that the first policy is perfect. The contribution is that the generator actively creates passing cases where urgency, perception limits, rear traffic, and oncoming gaps expose interpretable failures.
