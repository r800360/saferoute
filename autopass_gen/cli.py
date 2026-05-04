from __future__ import annotations

from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from autopass_gen.core.generator import ScenarioGenerator
from autopass_gen.core.io import load_scenario, save_scenario
from autopass_gen.sim.rollout import RolloutRunner
from autopass_gen.utils.plots import plot_metrics

app = typer.Typer(help="AutoPass-Gen initial prototype CLI")
console = Console()


@app.command()
def generate(n: int = 20, out_dir: str = "configs/generated", seed: int = 0):
    gen = ScenarioGenerator(seed=seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for spec in gen.sample(n):
        save_scenario(spec, out / f"{spec.scenario_id}.json")
    console.print(f"Generated {n} scenarios in {out}")


@app.command()
def run(
    scenario_dir: str = "configs/generated",
    out_dir: str = "runs/latest",
    policies: str = "autopass,no_pass,aggressive",
):
    runner = RolloutRunner(out_dir=out_dir)
    metrics = []
    for path in sorted(Path(scenario_dir).glob("*.json")):
        spec = load_scenario(path)
        for policy_name in [p.strip() for p in policies.split(",") if p.strip()]:
            metrics.append(runner.run(spec, policy_name=policy_name))
    csv_path = runner.evaluator.save_metrics_csv(metrics)
    plot_metrics(csv_path, Path(out_dir) / "figures")

    table = Table(title="AutoPass-Gen rollout summary")
    for col in ["policy", "n", "collisions", "failures", "avg_time_s", "pass_attempts"]:
        table.add_column(col)
    by_policy = {}
    for m in metrics:
        by_policy.setdefault(m.policy_name, []).append(m)
    for p, rows in by_policy.items():
        table.add_row(
            p,
            str(len(rows)),
            str(sum(r.collision for r in rows)),
            str(sum(r.generated_failure for r in rows)),
            f"{sum(r.time_to_goal_s for r in rows) / len(rows):.1f}",
            str(sum(r.pass_attempts for r in rows)),
        )
    console.print(table)
    console.print(f"Saved metrics to {csv_path}")


@app.command()
def demo(out_dir: str = "runs/demo", seed: int = 0):
    gen = ScenarioGenerator(seed=seed)
    scenario_dir = Path(out_dir) / "scenarios"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    for spec in gen.sample(12, prefix="demo"):
        save_scenario(spec, scenario_dir / f"{spec.scenario_id}.json")
    runner = RolloutRunner(out_dir=out_dir)
    metrics = []
    for path in sorted(scenario_dir.glob("*.json")):
        spec = load_scenario(path)
        for policy in ["autopass", "no_pass", "aggressive"]:
            metrics.append(runner.run(spec, policy))
    csv_path = runner.evaluator.save_metrics_csv(metrics)
    plot_metrics(csv_path, Path(out_dir) / "figures")
    console.print(f"Demo complete. Metrics: {csv_path}")


if __name__ == "__main__":
    app()
