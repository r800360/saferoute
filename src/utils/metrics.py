import math


class MetricsTracker:
    def __init__(self):
        self.collisions = 0
        self.red_light_violations = 0
        self.near_misses = 0

        self.total_risk = 0.0
        self.frames = 0

        self.min_dist_vehicle = float("inf")
        self.min_dist_pedestrian = float("inf")

    def update(self, scene):
        self.frames += 1
        self.total_risk += scene["risk"]["score"]

        for h in scene["hazards"]:
            d = h["forward_distance"]

            if h["kind"] == "vehicle":
                self.min_dist_vehicle = min(self.min_dist_vehicle, d)
                if d < 3.0:
                    self.near_misses += 1

            if h["kind"] == "pedestrian":
                self.min_dist_pedestrian = min(self.min_dist_pedestrian, d)
                if d < 4.0:
                    self.near_misses += 1

            if h["kind"] == "traffic_light":
                if "Red" in h.get("state", "") and d < 5.0:
                    self.red_light_violations += 1

    def report(self):
        return {
            "frames": self.frames,
            "avg_risk": self.total_risk / max(self.frames, 1),
            "near_misses": self.near_misses,
            "min_vehicle_distance": self.min_dist_vehicle,
            "min_ped_distance": self.min_dist_pedestrian,
            "red_light_violations": self.red_light_violations,
        }