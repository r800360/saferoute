import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import carla

# IMPORTANT: adjust this path if your CARLA install is elsewhere.
CARLA_PYTHONAPI = r"C:\carla\PythonAPI\carla"
sys.path.append(CARLA_PYTHONAPI)

from agents.navigation.behavior_agent import BehaviorAgent

from src.agents.perception import PerceptionAgent
from src.agents.planner import PlanningAgent
from src.agents.critic import SafetyCriticAgent


def spawn_ego(world):
    bp_lib = world.get_blueprint_library()
    bp = bp_lib.filter("vehicle.tesla.model3")[0]
    bp.set_attribute("role_name", "hero")

    spawn_points = world.get_map().get_spawn_points()
    random.shuffle(spawn_points)

    for sp in spawn_points:
        vehicle = world.try_spawn_actor(bp, sp)
        if vehicle is not None:
            return vehicle, spawn_points

    raise RuntimeError("Could not spawn ego vehicle.")


def get_agent_route_waypoints(agent, fallback_world, ego, destination, max_points=80):
    # BehaviorAgent internal route queue is version-dependent, so use fallback route if needed.
    carla_map = fallback_world.get_map()
    route = []
    wp = carla_map.get_waypoint(ego.get_location())
    dest_wp = carla_map.get_waypoint(destination)

    for _ in range(max_points):
        route.append(wp)
        next_wps = wp.next(2.0)
        if not next_wps:
            break
        next_wps.sort(key=lambda w: w.transform.location.distance(dest_wp.transform.location))
        wp = next_wps[0]
        if wp.transform.location.distance(dest_wp.transform.location) < 5.0:
            break

    return route


def draw_route(world, route_waypoints):
    for wp in route_waypoints[:80]:
        world.debug.draw_point(
            wp.transform.location + carla.Location(z=0.5),
            size=0.08,
            life_time=0.15,
        )

def follow_camera(world, vehicle, distance=8.0, height=4.0, pitch=-18.0):
    transform = vehicle.get_transform()
    yaw = transform.rotation.yaw
    yaw_rad = math.radians(yaw)

    back = carla.Location(
        x=-distance * math.cos(yaw_rad),
        y=-distance * math.sin(yaw_rad),
        z=height,
    )

    camera_loc = transform.location + back
    camera_rot = carla.Rotation(pitch=pitch, yaw=yaw, roll=0.0)
    world.get_spectator().set_transform(carla.Transform(camera_loc, camera_rot))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--town", default=None)
    parser.add_argument("--log", default="experiments/logs/demo_trace.jsonl")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    client = carla.Client(args.host, args.port)
    client.set_timeout(60.0)

    if args.town and args.reload:
        print(f"Loading {args.town}...")
        world = client.load_world(args.town)
        time.sleep(3.0)
    else:
        world = client.get_world()
        print(f"Using current world: {world.get_map().name}")

    original_settings = world.get_settings()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

    tm = client.get_trafficmanager(8000)
    tm.set_synchronous_mode(True)

    ego = None
    log_path = PROJECT_ROOT / args.log
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ego, spawn_points = spawn_ego(world)
        destination_tf = random.choice(spawn_points)
        destination = destination_tf.location

        # agent = BehaviorAgent(ego, behavior="normal")
        agent = BehaviorAgent(ego, behavior="cautious")
        agent.set_destination(destination)
        agent.set_target_speed(8)

        perception = PerceptionAgent()
        planner = PlanningAgent()
        critic = SafetyCriticAgent()

        start = time.time()
        frame = 0

        with open(log_path, "w", encoding="utf-8") as f:
            while time.time() - start < args.seconds:
                world.tick()
                follow_camera(world, ego)

                route = get_agent_route_waypoints(agent, world, ego, destination)
                draw_route(world, route)

                scene = perception.observe(world, ego, route)
                scene = planner.propose(scene)
                scene = critic.evaluate(scene)

                control = agent.run_step()

                # SafeRoute wrapper: let BehaviorAgent drive, but allow our critic to override.
                # action = scene["proposal"]["action"]
                # if action == "stop":
                #     control.throttle = 0.0
                #     control.brake = max(control.brake, 0.85)
                # elif action == "slow":
                #     control.throttle = min(control.throttle, 0.25)
                nearest = scene["hazards"][0] if scene["hazards"] else None

                if nearest and nearest["distance"] < 6.0:
                    control.throttle = 0.0
                    control.brake = 1.0
                    scene["proposal"] = {
                        "action": "emergency_stop",
                        "target_speed_mps": 0.0,
                        "reason": f"hard safety override: {nearest['kind']} at {nearest['distance']:.1f}m",
                    }
                elif scene["proposal"]["action"] == "stop":
                    control.throttle = 0.0
                    control.brake = max(control.brake, 0.9)
                elif scene["proposal"]["action"] == "slow":
                    control.throttle = min(control.throttle, 0.18)

                ego.apply_control(control)

                trace = {
                    "frame": frame,
                    "ego": scene["ego"],
                    "proposal": scene["proposal"],
                    "risk": scene["risk"],
                    "num_hazards": len(scene["hazards"]),
                    "nearest_hazard": scene["hazards"][0] if scene["hazards"] else None,
                    "control": {
                        "throttle": control.throttle,
                        "brake": control.brake,
                        "steer": control.steer,
                    },
                }
                f.write(json.dumps(trace) + "\n")

                if frame % 20 == 0:
                    print(
                        f"[{frame:04d}] "
                        f"action={scene['proposal']['action']} "
                        f"risk={scene['risk']['score']:.2f} "
                        f"speed={scene['ego']['speed_mps']:.2f} "
                        f"hazards={len(scene['hazards'])} "
                        f"brake={control.brake:.2f} steer={control.steer:.2f}"
                    )

                if agent.done():
                    print("Destination reached.")
                    break

                frame += 1

        print(f"\nSaved decision trace to {log_path}")

    finally:
        if ego is not None:
            ego.destroy()
        world.apply_settings(original_settings)
        tm.set_synchronous_mode(False)


if __name__ == "__main__":
    main()