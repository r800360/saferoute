# from typing import Any, Dict, List
# from src.maps.map_ir import (
#     build_route_graph,
#     detect_hazards,
#     annotate_edges_with_hazards,
#     make_scene_state,
# )


# class PerceptionAgent:
#     def observe(self, world: Any, ego_vehicle: Any, route_waypoints: List[Any]) -> Dict[str, Any]:
#         nodes, edges = build_route_graph(route_waypoints)
#         hazards = detect_hazards(world, ego_vehicle)
#         edges = annotate_edges_with_hazards(nodes, edges, hazards)
#         return make_scene_state(ego_vehicle, nodes, edges, hazards)
import math
import carla


def _speed_mps(actor):
    v = actor.get_velocity()
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def _forward_vector(transform):
    yaw = math.radians(transform.rotation.yaw)
    return carla.Vector3D(math.cos(yaw), math.sin(yaw), 0.0)


def _dot(a, b):
    return a.x * b.x + a.y * b.y + a.z * b.z


class PerceptionAgent:
    def observe(self, world, ego, route=None, lookahead=35.0):
        ego_tf = ego.get_transform()
        ego_loc = ego_tf.location
        fwd = _forward_vector(ego_tf)

        hazards = []

        for actor in world.get_actors():
            if actor.id == ego.id:
                continue

            kind = None
            if actor.type_id.startswith("vehicle."):
                kind = "vehicle"
            elif actor.type_id.startswith("walker."):
                kind = "pedestrian"
            elif actor.type_id.startswith("traffic.traffic_light"):
                kind = "traffic_light"

            if kind is None:
                continue

            loc = actor.get_location()
            rel = loc - ego_loc
            forward_dist = _dot(rel, fwd)

            if forward_dist < 0 or forward_dist > lookahead:
                continue

            dist = ego_loc.distance(loc)
            lateral_sq = max(dist * dist - forward_dist * forward_dist, 0.0)
            lateral_dist = math.sqrt(lateral_sq)

            # Ignore things not roughly in our driving corridor.
            corridor_width = 5.0 if kind != "pedestrian" else 7.0
            if lateral_dist > corridor_width:
                continue

            hazard = {
                "id": actor.id,
                "kind": kind,
                "distance": float(dist),
                "forward_distance": float(forward_dist),
                "lateral_distance": float(lateral_dist),
                "speed_mps": float(_speed_mps(actor)) if kind in ["vehicle", "pedestrian"] else 0.0,
            }

            if kind == "traffic_light":
                hazard["state"] = str(actor.state)

            hazards.append(hazard)

        hazards.sort(key=lambda h: h["forward_distance"])

        wp = world.get_map().get_waypoint(
            ego_loc,
            project_to_road=True,
            lane_type=carla.LaneType.Driving,
        )

        return {
            "ego": {
                "id": ego.id,
                "x": ego_loc.x,
                "y": ego_loc.y,
                "z": ego_loc.z,
                "yaw": ego_tf.rotation.yaw,
                "speed_mps": _speed_mps(ego),
                "road_id": wp.road_id if wp else None,
                "lane_id": wp.lane_id if wp else None,
                "junction": bool(wp.is_junction) if wp else False,
            },
            "route": route or [],
            "hazards": hazards,
            "proposal": {
                "action": "continue",
                "target_speed_mps": 6.0,
                "reason": "default cruising",
            },
            "risk": {
                "score": 0.0,
                "reasons": [],
            },
            "control": {},
        }