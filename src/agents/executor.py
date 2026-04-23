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