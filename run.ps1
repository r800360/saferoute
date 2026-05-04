python -m autopass_gen.cli generate --n 50 --out-dir configs/generated_50 --seed 0
python -m autopass_gen.cli demo --out-dir runs/demo_fixed_3
python -m autopass_gen.cli run --scenario-dir configs/generated_50 --out-dir runs/batch_50_deadline_fix --policies autopass,no_pass,aggressive

@'
import pandas as pd

df = pd.read_csv("runs/batch_50_deadline_fix/metrics.csv")
print(pd.crosstab(df["policy_name"], df["failure_type"]))
print()
print(df.groupby("policy_name")[["time_to_goal_s", "pass_attempts", "unsafe_passes"]].mean())
'@ | python