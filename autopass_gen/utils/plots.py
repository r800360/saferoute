from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def plot_metrics(metrics_csv: str | Path, out_dir: str | Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(metrics_csv)
    if df.empty:
        return

    summary = df.groupby("policy_name").agg(
        collision_rate=("collision", "mean"),
        failure_rate=("generated_failure", "mean"),
        avg_time_to_goal=("time_to_goal_s", "mean"),
        avg_pass_attempts=("pass_attempts", "mean"),
        unsafe_passes=("unsafe_passes", "sum"),
    )
    summary.to_csv(out_dir / "summary_by_policy.csv")

    ax = summary[["collision_rate", "failure_rate"]].plot(kind="bar")
    ax.set_title("Safety/failure rates by policy")
    ax.set_ylabel("rate")
    ax.figure.tight_layout()
    ax.figure.savefig(out_dir / "failure_rates.png", dpi=180)
    plt.close(ax.figure)

    ax = summary[["avg_time_to_goal", "avg_pass_attempts"]].plot(kind="bar")
    ax.set_title("Efficiency and pass behavior by policy")
    ax.figure.tight_layout()
    ax.figure.savefig(out_dir / "efficiency_passes.png", dpi=180)
    plt.close(ax.figure)
