from __future__ import annotations

import random
from typing import Iterable

from autopass_gen.core.schema import (
    EgoSpec,
    OcclusionSpec,
    RequestSpec,
    RouteSpec,
    ScenarioSpec,
    SensorSpec,
    VehicleSpec,
    WeatherSpec,
)


class ScenarioGenerator:
    """Samples and mutates the compact DSL from the design doc."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def sample(self, n: int, prefix: str = "sample") -> list[ScenarioSpec]:
        return [self._one(f"{prefix}_{i:04d}") for i in range(n)]

    def mutate_failures(self, failed: Iterable[ScenarioSpec], k: int = 2) -> list[ScenarioSpec]:
        out: list[ScenarioSpec] = []
        for spec in failed:
            for j in range(k):
                m = spec.model_copy(deep=True)
                m.scenario_id = f"{spec.scenario_id}_mut{j}"
                m.lead.distance_m = max(10.0, m.lead.distance_m + self.rng.uniform(-6, 4))
                m.lead.speed_mps = max(2.0, m.lead.speed_mps + self.rng.uniform(-1.5, 0.5))
                m.rear.distance_m = max(8.0, m.rear.distance_m + self.rng.uniform(-10, 6))
                m.oncoming.distance_m = max(25.0, m.oncoming.distance_m + self.rng.uniform(-25, 10))
                m.occlusion.severity = min(
                    1.0, max(0.0, m.occlusion.severity + self.rng.uniform(0.0, 0.2))
                )
                m.occlusion.sight_distance_m = max(
                    25.0, m.occlusion.sight_distance_m - self.rng.uniform(0, 20)
                )
                m.request.deadline_min = max(4.0, m.request.deadline_min - self.rng.uniform(0, 2))
                m.request.text = (
                    f"I am running late and need to arrive in {m.request.deadline_min:.0f} minutes."
                )
                out.append(m)
        return out

    def _one(self, scenario_id: str) -> ScenarioSpec:
        # deadline = self.rng.choice([5, 7, 10, 12, 18])
        deadline = self.rng.choice([1.0, 1.5, 2.0, 3.0, 5.0])
        urgent_words = "ASAP" if deadline <= 7 else "soon"
        occlusion_type = self.rng.choice(["none", "parked_cars", "curve", "junction"])
        severity = 0.0 if occlusion_type == "none" else self.rng.uniform(0.15, 0.85)
        return ScenarioSpec(
            scenario_id=scenario_id,
            request=RequestSpec(
                text=f"I need to get to the destination {urgent_words} in {deadline} minutes.",
                start="spawn_0",
                goal="spawn_20",
                deadline_min=float(deadline),
            ),
            # route=RouteSpec(length_m=self.rng.uniform(800, 1600)),
            # lightweight simulator uses short synthetic routes for fast closed-loop testing, while CARLA integration will use map-based routes
            route=RouteSpec(length_m=self.rng.uniform(350, 700)),
            ego=EgoSpec(speed_mps=self.rng.uniform(8.0, 12.5), desired_speed_mps=13.4),
            lead=VehicleSpec(
                distance_m=self.rng.uniform(16, 55),
                speed_mps=self.rng.uniform(3.5, 8.5),
                accel_mps2=self.rng.uniform(-0.5, 0.2),
            ),
            rear=VehicleSpec(
                distance_m=self.rng.uniform(12, 70), speed_mps=self.rng.uniform(8, 16)
            ),
            oncoming=VehicleSpec(
                distance_m=self.rng.uniform(45, 220), speed_mps=self.rng.uniform(8, 16)
            ),
            oncoming_gap_time_s=self.rng.uniform(3, 12),
            occlusion=OcclusionSpec(
                type=occlusion_type,
                severity=severity,
                sight_distance_m=self.rng.uniform(45, 160),
            ),
            weather=WeatherSpec(rain=self.rng.random() * 0.8, fog=self.rng.random() * 0.7),
            sensor=SensorSpec(mode=self.rng.choice(["privileged", "rgb_depth"]), noise_std_m=0.4),
        )
