# from typing import Any, Dict


# class PlanningAgent:
#     def propose(self, scene: Dict[str, Any]) -> Dict[str, Any]:
#         hazards = scene.get("hazards", [])
#         ego_speed = scene["ego"]["speed_mps"]

#         nearest_ped = next((h for h in hazards if h["kind"] == "pedestrian"), None)
#         nearest_vehicle = next((h for h in hazards if h["kind"] == "vehicle"), None)
#         nearest_light = next((h for h in hazards if h["kind"] == "traffic_light"), None)

#         action = "continue"
#         target_speed = 8.0
#         reason = "route is clear"

#         if nearest_ped and nearest_ped["distance"] < 12.0:
#             action = "stop"
#             target_speed = 0.0
#             reason = "pedestrian hazard within stopping region"
#         elif nearest_vehicle and nearest_vehicle["distance"] < 10.0:
#             action = "slow"
#             target_speed = 3.0
#             reason = "nearby vehicle hazard"
#         elif nearest_light and nearest_light["distance"] < 15.0 and "Red" in nearest_light["note"]:
#             action = "stop"
#             target_speed = 0.0
#             reason = "red traffic light nearby"
#         elif ego_speed > 10.0:
#             action = "slow"
#             target_speed = 6.0
#             reason = "ego speed exceeds conservative prototype limit"

#         scene["proposal"] = {
#             "action": action,
#             "target_speed_mps": target_speed,
#             "reason": reason,
#         }
#         return scene
class PlanningAgent:
    def propose(self, scene):
        hazards = scene["hazards"]
        ego = scene["ego"]

        action = "continue"
        target_speed = 7.0
        reason = "clear route"

        nearest = hazards[0] if hazards else None

        if nearest:
            d = nearest["forward_distance"]
            kind = nearest["kind"]

            if kind == "traffic_light" and "Red" in nearest.get("state", "") and d < 18.0:
                action = "stop"
                target_speed = 0.0
                reason = f"red light ahead at {d:.1f}m"

            elif kind == "pedestrian" and d < 15.0:
                action = "stop"
                target_speed = 0.0
                reason = f"pedestrian ahead at {d:.1f}m"

            elif kind == "vehicle" and d < 10.0:
                action = "slow"
                target_speed = 2.5
                reason = f"lead vehicle close at {d:.1f}m"

            elif kind == "vehicle" and d < 20.0:
                action = "slow"
                target_speed = 4.0
                reason = f"lead vehicle ahead at {d:.1f}m"

        if ego["junction"] and action == "continue":
            action = "slow"
            target_speed = 4.5
            reason = "approaching or inside junction"

        scene["proposal"] = {
            "action": action,
            "target_speed_mps": target_speed,
            "reason": reason,
        }

        return scene