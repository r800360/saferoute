import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

CARLA_PYTHONAPI = r"C:\carla\PythonAPI\carla"
sys.path.append(CARLA_PYTHONAPI)

import carla

from src.agents.perception import PerceptionAgent
from src.agents.planner import PlanningAgent
from src.agents.critic import SafetyCriticAgent
from src.agents.executor import ExecutionAgent


def speed_mps(actor):
    v = actor.get_velocity()
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def follow_camera(world, vehicle, distance=9.0, height=4.0, pitch=-18.0):
    tf = vehicle.get_transform()
    yaw = math.radians(tf.rotation.yaw)

    loc = tf.location + carla.Location(
        x=-distance * math.cos(yaw),
        y=-distance * math.sin(yaw),
        z=height,
    )
    rot = carla.Rotation(pitch=pitch, yaw=tf.rotation.yaw, roll=0)
    world.get_spectator().set_transform(carla.Transform(loc, rot))


def spawn_vehicle_at(world, index=0, role="hero"):
    bp = world.get_blueprint_library().filter("vehicle.tesla.model3")[0]
    bp.set_attribute("role_name", role)

    spawn_points = world.get_map().get_spawn_points()
    tf = spawn_points[index % len(spawn_points)]

    vehicle = world.try_spawn_actor(bp, tf)
    if vehicle is None:
        raise RuntimeError(f"Could not spawn vehicle at spawn index {index}")
    return vehicle


def get_forward_transform(world, ego, distance=25.0, lateral=0.0):
    carla_map = world.get_map()
    wp = carla_map.get_waypoint(ego.get_location(), project_to_road=True)
    next_wps = wp.next(distance)
    if not next_wps:
        return wp.transform

    target_wp = next_wps[0]
    tf = target_wp.transform

    yaw = math.radians(tf.rotation.yaw)
    right = carla.Location(x=-math.sin(yaw), y=math.cos(yaw), z=0)

    tf.location = tf.location + lateral * right + carla.Location(z=0.5)
    return tf


def spawn_stopped_vehicle(world, ego, distance=28.0):
    bp_lib = world.get_blueprint_library()
    bp = bp_lib.filter("vehicle.lincoln.mkz_2020")[0]
    tf = get_forward_transform(world, ego, distance=distance, lateral=0.0)

    actor = world.try_spawn_actor(bp, tf)
    if actor is None:
        print("WARNING: failed to spawn stopped vehicle")
        return None

    actor.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
    return actor


def spawn_pedestrian_crossing(world, ego, distance=24.0):
    bp_lib = world.get_blueprint_library()
    walker_bp = random.choice(bp_lib.filter("walker.pedestrian.*"))
    controller_bp = bp_lib.find("controller.ai.walker")

    start_tf = get_forward_transform(world, ego, distance=distance, lateral=4.0)
    end_tf = get_forward_transform(world, ego, distance=distance, lateral=-4.0)

    walker = world.try_spawn_actor(walker_bp, start_tf)
    if walker is None:
        print("WARNING: failed to spawn pedestrian")
        return None, None

    controller = world.spawn_actor(controller_bp, carla.Transform(), walker)
    controller.start()
    controller.go_to_location(end_tf.location)
    controller.set_max_speed(1.4)

    return walker, controller


def spawn_slow_lead_vehicle(world, ego, tm, distance=30.0):
    bp_lib = world.get_blueprint_library()
    bp = bp_lib.filter("vehicle.audi.tt")[0]
    tf = get_forward_transform(world, ego, distance=distance, lateral=0.0)

    actor = world.try_spawn_actor(bp, tf)
    if actor is None:
        print("WARNING: failed to spawn slow lead vehicle")
        return None

    actor.set_autopilot(True, tm.get_port())
    tm.vehicle_percentage_speed_difference(actor, 80.0)
    tm.distance_to_leading_vehicle(actor, 2.0)
    return actor


def apply_saferoute(scene, executor):
    scene = executor.apply(scene)
    return scene


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--town", default="Town03")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--seconds", type=float, default=45.0)
    parser.add_argument("--mode", choices=["tm", "saferoute"], default="saferoute")
    parser.add_argument(
        "--scenario",
        choices=["pedestrian_crossing", "stopped_vehicle", "slow_lead_vehicle"],
        default="pedestrian_crossing",
    )
    parser.add_argument("--spawn-index", type=int, default=0)
    parser.add_argument("--log", default=None)
    args = parser.parse_args()

    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(60.0)

    if args.reload:
        world = client.load_world(args.town)
        time.sleep(3)
    else:
        world = client.get_world()

    original_settings = world.get_settings()

    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

    tm = client.get_trafficmanager(8000)
    tm.set_synchronous_mode(True)
    tm.set_global_distance_to_leading_vehicle(4.0)

    ego = None
    actors = []
    controllers = []

    if args.log is None:
        args.log = f"experiments/logs/stress_{args.scenario}_{args.mode}.jsonl"

    log_path = PROJECT_ROOT / args.log
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ego = spawn_vehicle_at(world, args.spawn_index, role="hero")

        for _ in range(20):
            world.tick()

        ego.set_autopilot(True, tm.get_port())
        tm.ignore_lights_percentage(ego, 0.0)
        tm.ignore_signs_percentage(ego, 0.0)
        tm.ignore_vehicles_percentage(ego, 0.0)
        tm.ignore_walkers_percentage(ego, 0.0)
        tm.distance_to_leading_vehicle(ego, 5.0)
        tm.vehicle_percentage_speed_difference(ego, 35.0)

        if args.scenario == "pedestrian_crossing":
            walker, controller = spawn_pedestrian_crossing(world, ego)
            if walker:
                actors.append(walker)
            if controller:
                controllers.append(controller)

        elif args.scenario == "stopped_vehicle":
            stopped = spawn_stopped_vehicle(world, ego)
            if stopped:
                actors.append(stopped)

        elif args.scenario == "slow_lead_vehicle":
            lead = spawn_slow_lead_vehicle(world, ego, tm)
            if lead:
                actors.append(lead)

        perception = PerceptionAgent()
        planner = PlanningAgent()
        critic = SafetyCriticAgent()
        executor = ExecutionAgent(tm, ego)

        frame = 0
        start = time.time()

        min_hazard_dist = float("inf")
        near_miss_frames = 0
        intervention_frames = 0

        with open(log_path, "w", encoding="utf-8") as f:
            while time.time() - start < args.seconds:
                world.tick()
                follow_camera(world, ego)

                scene = perception.observe(world, ego)
                scene = planner.propose(scene)
                scene = critic.evaluate(scene)

                if args.mode == "saferoute":
                    scene = apply_saferoute(scene, executor)
                else:
                    control = ego.get_control()
                    scene["control"] = {
                        "mode": "tm_only",
                        "throttle": float(control.throttle),
                        "brake": float(control.brake),
                        "steer": float(control.steer),
                    }

                if scene["proposal"]["action"] != "continue":
                    intervention_frames += 1

                if scene["hazards"]:
                    nearest = scene["hazards"][0]
                    d = nearest["forward_distance"]
                    min_hazard_dist = min(min_hazard_dist, d)
                    if d < 4.0:
                        near_miss_frames += 1

                trace = {
                    "frame": frame,
                    "time_s": frame * settings.fixed_delta_seconds,
                    "mode": args.mode,
                    "scenario": args.scenario,
                    "ego_speed_mps": speed_mps(ego),
                    "proposal": scene["proposal"],
                    "risk": scene["risk"],
                    "hazards": scene["hazards"][:6],
                    "control": scene["control"],
                    "near_miss_frames": near_miss_frames,
                    "min_hazard_dist": min_hazard_dist,
                }
                f.write(json.dumps(trace) + "\n")

                if frame % 20 == 0:
                    print(
                        f"[{frame:04d}] "
                        f"{args.mode} | {args.scenario} | "
                        f"speed={speed_mps(ego):.2f} "
                        f"action={scene['proposal']['action']} "
                        f"risk={scene['risk']['score']:.2f} "
                        f"hazards={len(scene['hazards'])} "
                        f"min_d={min_hazard_dist:.1f}"
                    )

                frame += 1

        print("\n=== Stress Test Summary ===")
        print(f"Scenario: {args.scenario}")
        print(f"Mode: {args.mode}")
        print(f"Frames: {frame}")
        print(f"Near-miss frames: {near_miss_frames}")
        print(f"Intervention frames: {intervention_frames}")
        print(f"Minimum hazard distance: {min_hazard_dist:.2f} m")
        print(f"Saved log: {log_path}")

    finally:
        if ego is not None:
            ego.set_autopilot(False)
            ego.destroy()

        for controller in controllers:
            controller.stop()
            controller.destroy()

        for actor in actors:
            actor.destroy()

        world.apply_settings(original_settings)
        tm.set_synchronous_mode(False)


if __name__ == "__main__":
    main()