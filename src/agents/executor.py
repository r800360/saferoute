# from typing import Any, Dict
# import math


# class ExecutionAgent:
#     def __init__(self, max_steer: float = 0.35):
#         self.max_steer = max_steer

#     def _angle_error_deg(self, ego_yaw: float, target_yaw: float) -> float:
#         err = target_yaw - ego_yaw
#         while err > 180:
#             err -= 360
#         while err < -180:
#             err += 360
#         return err

#     def control(self, scene: Dict[str, Any]) -> Dict[str, Any]:
#         proposal = scene.get("proposal") or {"action": "continue", "target_speed_mps": 6.0}
#         ego = scene["ego"]
#         route_nodes = scene["route"]["nodes"]

#         target_speed = float(proposal.get("target_speed_mps", 6.0))
#         speed = float(ego["speed_mps"])

#         throttle = 0.35 if speed < target_speed else 0.0
#         brake = 0.0 if speed <= target_speed + 0.5 else 0.25

#         if proposal["action"] == "stop":
#             throttle = 0.0
#             brake = 0.8

#         steer = 0.0
#         if len(route_nodes) >= 2:
#             target = route_nodes[min(3, len(route_nodes) - 1)]
#             desired_yaw = math.degrees(math.atan2(target["y"] - ego["y"], target["x"] - ego["x"]))
#             err = self._angle_error_deg(float(ego["yaw"]), desired_yaw)
#             steer = max(-self.max_steer, min(self.max_steer, err / 45.0 * self.max_steer))

#         scene["control"] = {
#             "throttle": float(throttle),
#             "brake": float(brake),
#             "steer": float(steer),
#             "action": proposal["action"],
#         }
#         return scene
class ExecutionAgent:
    """
    SafeRoute execution layer.

    Important design choice:
    Traffic Manager still controls steering. SafeRoute only changes the target
    speed behavior. This avoids the wall-crashing issue caused by unstable
    manual steering overrides.
    """

    def __init__(self, traffic_manager, ego):
        self.tm = traffic_manager
        self.ego = ego

    def apply(self, scene):
        action = scene["proposal"]["action"]

        if action == "stop":
            # 100% slower than speed limit is approximately a stop request.
            self.tm.vehicle_percentage_speed_difference(self.ego, 100.0)
            mode = "tm_stop"

        elif action == "slow":
            self.tm.vehicle_percentage_speed_difference(self.ego, 75.0)
            mode = "tm_slow"

        else:
            self.tm.vehicle_percentage_speed_difference(self.ego, 45.0)
            mode = "tm_continue"

        control = self.ego.get_control()

        scene["control"] = {
            "mode": mode,
            "throttle": float(control.throttle),
            "brake": float(control.brake),
            "steer": float(control.steer),
        }

        return scene