class SafetyCriticAgent:
    def evaluate(self, scene):
        score = 0.0
        reasons = []

        for h in scene["hazards"]:
            d = h["forward_distance"]
            kind = h["kind"]

            if kind == "pedestrian":
                if d < 8:
                    score += 0.9
                    reasons.append(f"pedestrian very close: {d:.1f}m")
                elif d < 15:
                    score += 0.5
                    reasons.append(f"pedestrian ahead: {d:.1f}m")

            elif kind == "vehicle":
                if d < 6:
                    score += 0.7
                    reasons.append(f"vehicle very close: {d:.1f}m")
                elif d < 12:
                    score += 0.35
                    reasons.append(f"vehicle ahead: {d:.1f}m")

            elif kind == "traffic_light" and "Red" in h.get("state", ""):
                if d < 15:
                    score += 0.8
                    reasons.append(f"red light close: {d:.1f}m")

        if scene["ego"]["junction"]:
            score += 0.15
            reasons.append("junction context")

        score = min(score, 1.0)

        proposal = scene["proposal"]

        if score >= 0.75:
            proposal = {
                "action": "stop",
                "target_speed_mps": 0.0,
                "reason": "critic override: high risk",
            }
        elif score >= 0.35 and proposal["action"] == "continue":
            proposal = {
                "action": "slow",
                "target_speed_mps": 3.0,
                "reason": "critic override: moderate risk",
            }

        scene["risk"] = {
            "score": score,
            "reasons": reasons,
        }
        scene["proposal"] = proposal
        return scene