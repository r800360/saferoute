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