from __future__ import annotations

import random
from autopass_gen.core.schema import PassState, ScenarioSpec, UrgencyContext, EgoState


class PerceptionMapTools:
    """State estimator. Starts with privileged simulator state; can inject sensor degradation."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def estimate(
        self, spec: ScenarioSpec, urgency: UrgencyContext, ego: EgoState, t_s: float
    ) -> PassState:
        noise = spec.sensor.noise_std_m if spec.sensor.mode != "privileged" else 0.0
        dropout = self.rng.random() < spec.sensor.dropout_prob
        weather_penalty = 30.0 * spec.weather.fog + 15.0 * spec.weather.rain
        visibility = max(
            10.0,
            spec.occlusion.sight_distance_m * (1 - 0.55 * spec.occlusion.severity)
            - weather_penalty,
        )
        if dropout:
            visibility *= 0.45

        def noisy(x: float) -> float:
            return max(0.0, x + self.rng.gauss(0.0, noise))

        lead_x = spec.lead.distance_m + spec.lead.speed_mps * t_s
        rear_x = -spec.rear.distance_m + spec.rear.speed_mps * t_s
        oncoming_x = spec.oncoming.distance_m - spec.oncoming.speed_mps * t_s

        lead_distance = lead_x - ego.x_m
        rear_distance = ego.x_m - rear_x
        oncoming_distance = oncoming_x - ego.x_m

        return PassState(
            t_s=t_s,
            ego=ego,
            lead_distance_m=noisy(lead_distance),
            lead_speed_mps=spec.lead.speed_mps,
            rear_distance_m=noisy(rear_distance),
            rear_speed_mps=spec.rear.speed_mps,
            oncoming_distance_m=noisy(oncoming_distance),
            oncoming_speed_mps=spec.oncoming.speed_mps,
            visibility_m=visibility,
            deadline_min=urgency.deadline_min,
            urgency=urgency.urgency_level,
            delay_cost=urgency.delay_cost,
        )
