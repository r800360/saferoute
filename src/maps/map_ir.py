from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import math


@dataclass
class RouteNode:
    idx: int
    x: float
    y: float
    z: float
    yaw: float
    road_id: int
    lane_id: int
    is_junction: bool


@dataclass
class RouteEdge:
    src: int
    dst: int
    distance: float
    hazard_cost: float = 0.0
    junction_cost: float = 0.0
    total_cost: float = 0.0


@dataclass
class Hazard:
    kind: str
    actor_id: int
    distance: float
    x: float
    y: float
    note: str


def _dist_xy(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def waypoint_to_node(idx: int, wp: Any) -> RouteNode:
    loc = wp.transform.location
    rot = wp.transform.rotation
    return RouteNode(
        idx=idx,
        x=float(loc.x),
        y=float(loc.y),
        z=float(loc.z),
        yaw=float(rot.yaw),
        road_id=int(wp.road_id),
        lane_id=int(wp.lane_id),
        is_junction=bool(wp.is_junction),
    )


def build_route_graph(route_waypoints: List[Any]) -> Tuple[List[RouteNode], List[RouteEdge]]:
    nodes = [waypoint_to_node(i, wp) for i, wp in enumerate(route_waypoints)]
    edges: List[RouteEdge] = []

    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        d = math.hypot(a.x - b.x, a.y - b.y)
        junction_cost = 3.0 if (a.is_junction or b.is_junction) else 0.0
        edges.append(
            RouteEdge(
                src=i,
                dst=i + 1,
                distance=d,
                junction_cost=junction_cost,
                total_cost=d + junction_cost,
            )
        )

    return nodes, edges


def detect_hazards(world: Any, ego_vehicle: Any, radius_m: float = 25.0) -> List[Hazard]:
    ego_loc = ego_vehicle.get_location()
    hazards: List[Hazard] = []

    for actor in world.get_actors():
        if actor.id == ego_vehicle.id:
            continue

        type_id = actor.type_id
        if not (
            type_id.startswith("vehicle.")
            or type_id.startswith("walker.")
            or type_id.startswith("traffic.traffic_light")
        ):
            continue

        loc = actor.get_location()
        d = _dist_xy(ego_loc, loc)
        if d > radius_m:
            continue

        if type_id.startswith("vehicle."):
            kind = "vehicle"
            note = "nearby dynamic vehicle"
        elif type_id.startswith("walker."):
            kind = "pedestrian"
            note = "nearby pedestrian"
        else:
            kind = "traffic_light"
            try:
                note = f"traffic light state: {actor.get_state()}"
            except Exception:
                note = "traffic light nearby"

        hazards.append(
            Hazard(
                kind=kind,
                actor_id=int(actor.id),
                distance=float(d),
                x=float(loc.x),
                y=float(loc.y),
                note=note,
            )
        )

    hazards.sort(key=lambda h: h.distance)
    return hazards


def annotate_edges_with_hazards(
    nodes: List[RouteNode],
    edges: List[RouteEdge],
    hazards: List[Hazard],
    hazard_radius_m: float = 12.0,
) -> List[RouteEdge]:
    new_edges: List[RouteEdge] = []

    for edge in edges:
        dst = nodes[edge.dst]
        hazard_cost = 0.0

        for h in hazards:
            d = math.hypot(dst.x - h.x, dst.y - h.y)
            if d < hazard_radius_m:
                if h.kind == "pedestrian":
                    hazard_cost += 10.0 * (1.0 - d / hazard_radius_m)
                elif h.kind == "vehicle":
                    hazard_cost += 5.0 * (1.0 - d / hazard_radius_m)
                elif h.kind == "traffic_light":
                    hazard_cost += 4.0 * (1.0 - d / hazard_radius_m)

        total = edge.distance + edge.junction_cost + hazard_cost
        new_edges.append(
            RouteEdge(
                src=edge.src,
                dst=edge.dst,
                distance=edge.distance,
                hazard_cost=hazard_cost,
                junction_cost=edge.junction_cost,
                total_cost=total,
            )
        )

    return new_edges


def make_scene_state(
    ego_vehicle: Any,
    route_nodes: List[RouteNode],
    route_edges: List[RouteEdge],
    hazards: List[Hazard],
    max_route_nodes: int = 12,
) -> Dict[str, Any]:
    ego_tf = ego_vehicle.get_transform()
    ego_vel = ego_vehicle.get_velocity()
    speed = math.sqrt(ego_vel.x**2 + ego_vel.y**2 + ego_vel.z**2)

    return {
        "ego": {
            "x": float(ego_tf.location.x),
            "y": float(ego_tf.location.y),
            "z": float(ego_tf.location.z),
            "yaw": float(ego_tf.rotation.yaw),
            "speed_mps": float(speed),
        },
        "route": {
            "nodes": [asdict(n) for n in route_nodes[:max_route_nodes]],
            "edges": [asdict(e) for e in route_edges[: max_route_nodes - 1]],
        },
        "hazards": [asdict(h) for h in hazards[:10]],
        "proposal": None,
        "risk": None,
        "control": None,
    }