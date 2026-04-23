# from typing import Any, Dict


# class SafetyCriticAgent:
#     def evaluate(self, scene: Dict[str, Any]) -> Dict[str, Any]:
#         hazards = scene.get("hazards", [])
#         proposal = scene.get("proposal") or {"action": "continue"}

#         risk = 0.0
#         explanations = []

#         for h in hazards:
#             d = max(float(h["distance"]), 1e-3)

#             if h["kind"] == "pedestrian":
#                 contribution = max(0.0, 15.0 - d) / 15.0
#                 risk += 1.5 * contribution
#             elif h["kind"] == "vehicle":
#                 contribution = max(0.0, 12.0 - d) / 12.0
#                 risk += 1.0 * contribution
#             elif h["kind"] == "traffic_light" and "Red" in h["note"]:
#                 contribution = max(0.0, 18.0 - d) / 18.0
#                 risk += 1.2 * contribution
#             else:
#                 contribution = 0.0

#             if contribution > 0:
#                 explanations.append(f"{h['kind']} at {d:.1f}m contributes risk {contribution:.2f}")

#         approved = True
#         override = None

#         if risk > 1.0 and proposal["action"] == "continue":
#             approved = False
#             override = {
#                 "action": "slow",
#                 "target_speed_mps": 2.0,
#                 "reason": "critic override: risk too high for continue",
#             }

#         if risk > 1.8:
#             approved = False
#             override = {
#                 "action": "stop",
#                 "target_speed_mps": 0.0,
#                 "reason": "critic override: high-risk scene",
#             }

#         scene["risk"] = {
#             "score": float(risk),
#             "approved": approved,
#             "explanations": explanations,
#         }

#         if override is not None:
#             scene["proposal"] = override

#         return scene
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