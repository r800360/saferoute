from __future__ import annotations

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Decision(str, Enum):
    PASS = "pass"
    WAIT = "wait"
    REPLAN = "replan"


class FailureType(str, Enum):
    NONE = "none"
    UNSAFE_PASS = "unsafe_pass"
    MISSED_SAFE_PASS = "missed_safe_pass"
    OVER_CONSERVATIVE_DELAY = "over_conservative_delay"
    SENSOR_MODE_FAILURE = "sensor_mode_failure"
    COLLISION = "collision"


class RequestSpec(BaseModel):
    text: str = "I need to get to the destination in 10 minutes."
    start: str = "A"
    goal: str = "B"
    deadline_min: float = 10.0
    reason: str = "time sensitive trip"


class RouteSpec(BaseModel):
    town: str = "Town04"
    start: str = "spawn_0"
    goal: str = "spawn_20"
    lane_type: Literal["two_lane", "urban", "rural"] = "two_lane"
    length_m: float = 1200.0
    speed_limit_mps: float = 13.4


class VehicleSpec(BaseModel):
    distance_m: float = 30.0
    speed_mps: float = 6.0
    accel_mps2: float = 0.0


class EgoSpec(BaseModel):
    speed_mps: float = 10.0
    accel_mps2: float = 1.0
    desired_speed_mps: float = 13.4


class OcclusionSpec(BaseModel):
    type: Literal["none", "parked_cars", "curve", "junction"] = "none"
    severity: float = Field(default=0.0, ge=0.0, le=1.0)
    sight_distance_m: float = 120.0


class WeatherSpec(BaseModel):
    rain: float = Field(default=0.0, ge=0.0, le=1.0)
    fog: float = Field(default=0.0, ge=0.0, le=1.0)
    sun_angle: float = 45.0


class SensorSpec(BaseModel):
    mode: Literal["privileged", "rgb_depth", "rgb_only"] = "privileged"
    noise_std_m: float = 0.25
    dropout_prob: float = Field(default=0.0, ge=0.0, le=1.0)


class ScenarioSpec(BaseModel):
    scenario_id: str
    request: RequestSpec = Field(default_factory=RequestSpec)
    route: RouteSpec = Field(default_factory=RouteSpec)
    ego: EgoSpec = Field(default_factory=EgoSpec)
    lead: VehicleSpec = Field(default_factory=lambda: VehicleSpec(distance_m=25, speed_mps=5))
    rear: VehicleSpec = Field(default_factory=lambda: VehicleSpec(distance_m=40, speed_mps=11))
    oncoming: VehicleSpec = Field(default_factory=lambda: VehicleSpec(distance_m=140, speed_mps=12))
    oncoming_gap_time_s: float = 8.0
    occlusion: OcclusionSpec = Field(default_factory=OcclusionSpec)
    weather: WeatherSpec = Field(default_factory=WeatherSpec)
    sensor: SensorSpec = Field(default_factory=SensorSpec)


class UrgencyContext(BaseModel):
    start: str
    goal: str
    deadline_min: float
    urgency_level: Literal["low", "medium", "high"]
    delay_cost: float
    parsed_from: str


class EgoState(BaseModel):
    x_m: float = 0.0
    speed_mps: float = 10.0
    lane: Literal["current", "passing"] = "current"


class PassState(BaseModel):
    t_s: float
    ego: EgoState
    lead_distance_m: float
    lead_speed_mps: float
    rear_distance_m: float
    rear_speed_mps: float
    oncoming_distance_m: float
    oncoming_speed_mps: float
    visibility_m: float
    deadline_min: float
    urgency: str
    delay_cost: float
    decision: Optional[Decision] = None
    risk: float = 0.0
    critic_approved: bool = False
    reason: str = ""


class RolloutMetrics(BaseModel):
    scenario_id: str
    policy_name: str
    collision: bool
    route_completed: bool
    time_to_goal_s: float
    pass_attempts: int
    unsafe_passes: int
    min_ttc_s: float
    generated_failure: bool
    failure_type: FailureType
    final_decision: Optional[Decision] = None
    trace_path: str
