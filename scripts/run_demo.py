import argparse
import json
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import carla

from src.agents.perception import PerceptionAgent
from src.agents.planner import PlanningAgent
from src.agents.critic import SafetyCriticAgent
from src.agents.executor import ExecutionAgent


def draw_route(world, route_waypoints, life_time=0.2):
    for wp in route_waypoints[:60]:
        loc = wp.transform.location + carla.Location(z=0.6)
        world.debug.draw_point(loc, size=0.08, life_time=life_time)


def make_route(world, ego_vehicle, destination, step_m=2.0, max_points=80):
    carla_map = world.get_map()
    current_wp = carla_map.get_waypoint(ego_vehicle.get_location())
    dest_wp = carla_map.get_waypoint(destination.location)

    route = [current_wp]
    wp = current_wp

    for _ in range(max_points - 1):
        next_wps = wp.next(step_m)
        if not next_wps:
            break

        next_wps.sort(
            key=lambda candidate: candidate.transform.location.distance(dest_wp.transform.location)
        )
        wp = next_wps[0]
        route.append(wp)

        if wp.transform.location.distance(dest_wp.transform.location) < 5.0:
            break

    return route


def spawn_ego(world):
    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter("vehicle.tesla.model3")[0]
    spawn_points = world.get_map().get_spawn_points()
    random.shuffle(spawn_points)

    for sp in spawn_points:
        vehicle = world.try_spawn_actor(vehicle_bp, sp)
        if vehicle is not None:
            return vehicle, spawn_points

    raise RuntimeError("Could not spawn ego vehicle. Try restarting CARLA or changing map.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--town", default=None)
    parser.add_argument("--log", default="experiments/logs/demo_trace.jsonl")
    args = parser.parse_args()

    client = carla.Client(args.host, args.port)
    client.set_timeout(10.0)

    if args.town:
        world = client.load_world(args.town)
    else:
        world = client.get_world()

    settings = world.get_settings()
    original_settings = settings

    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

    traffic_manager = client.get_trafficmanager()
    traffic_manager.set_synchronous_mode(True)

    ego = None
    log_path = PROJECT_ROOT / args.log
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ego, spawn_points = spawn_ego(world)
        ego.set_autopilot(False)

        destination = random.choice(spawn_points)
        route = make_route(world, ego, destination)

        perception = PerceptionAgent()
        planner = PlanningAgent()
        critic = SafetyCriticAgent()
        executor = ExecutionAgent()

        start = time.time()
        frame = 0

        with open(log_path, "w", encoding="utf-8") as f:
            while time.time() - start < args.seconds:
                world.tick()
                draw_route(world, route)

                scene = perception.observe(world, ego, route)
                scene = planner.propose(scene)
                scene = critic.evaluate(scene)
                scene = executor.control(scene)

                ctrl = scene["control"]
                ego.apply_control(
                    carla.VehicleControl(
                        throttle=ctrl["throttle"],
                        steer=ctrl["steer"],
                        brake=ctrl["brake"],
                    )
                )

                trace = {
                    "frame": frame,
                    "ego": scene["ego"],
                    "proposal": scene["proposal"],
                    "risk": scene["risk"],
                    "control": scene["control"],
                    "num_hazards": len(scene["hazards"]),
                    "nearest_hazard": scene["hazards"][0] if scene["hazards"] else None,
                }
                f.write(json.dumps(trace) + "\n")

                if frame % 20 == 0:
                    print(
                        f"[{frame:04d}] action={scene['proposal']['action']} "
                        f"risk={scene['risk']['score']:.2f} "
                        f"speed={scene['ego']['speed_mps']:.2f} "
                        f"hazards={len(scene['hazards'])}"
                    )

                frame += 1

        print(f"\nSaved decision trace to {log_path}")

    finally:
        if ego is not None:
            ego.destroy()
        world.apply_settings(original_settings)
        traffic_manager.set_synchronous_mode(False)


if __name__ == "__main__":
    main()