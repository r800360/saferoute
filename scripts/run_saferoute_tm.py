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

from src.utils.metrics import MetricsTracker


def speed_mps(vehicle):
    v = vehicle.get_velocity()
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def spawn_ego(world):
    bp_lib = world.get_blueprint_library()
    bp = bp_lib.filter("vehicle.tesla.model3")[0]
    bp.set_attribute("role_name", "hero")

    spawn_points = world.get_map().get_spawn_points()
    random.shuffle(spawn_points)

    for sp in spawn_points:
        vehicle = world.try_spawn_actor(bp, sp)
        if vehicle is not None:
            return vehicle

    raise RuntimeError("Could not spawn ego vehicle.")


def spawn_npc_vehicles(client, world, tm, count=20):
    bp_lib = world.get_blueprint_library()
    vehicle_bps = bp_lib.filter("vehicle.*")
    spawn_points = world.get_map().get_spawn_points()
    random.shuffle(spawn_points)

    actors = []

    for sp in spawn_points[:count]:
        bp = random.choice(vehicle_bps)

        if bp.has_attribute("role_name"):
            bp.set_attribute("role_name", "autopilot")

        actor = world.try_spawn_actor(bp, sp)
        if actor is not None:
            actor.set_autopilot(True, tm.get_port())
            tm.vehicle_percentage_speed_difference(actor, random.uniform(20.0, 55.0))
            actors.append(actor)

    return actors


def follow_camera(world, vehicle, distance=9.0, height=4.0, pitch=-18.0):
    tf = vehicle.get_transform()
    yaw = math.radians(tf.rotation.yaw)

    camera_loc = tf.location + carla.Location(
        x=-distance * math.cos(yaw),
        y=-distance * math.sin(yaw),
        z=height,
    )

    camera_rot = carla.Rotation(
        pitch=pitch,
        yaw=tf.rotation.yaw,
        roll=0.0,
    )

    world.get_spectator().set_transform(carla.Transform(camera_loc, camera_rot))


def draw_hazards(world, scene):
    for h in scene["hazards"][:8]:
        actor = world.get_actor(h["id"])
        if actor is None:
            continue

        loc = actor.get_location() + carla.Location(z=1.5)
        label = f"{h['kind']} {h['forward_distance']:.1f}m"

        world.debug.draw_string(
            loc,
            label,
            draw_shadow=False,
            life_time=0.08,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--town", default="Town03")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--npc", type=int, default=20)
    parser.add_argument("--log", default="experiments/logs/saferoute_tm_trace.jsonl")
    args = parser.parse_args()

    client = carla.Client(args.host, args.port)
    client.set_timeout(60.0)

    if args.reload:
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
    tm.set_global_distance_to_leading_vehicle(4.0)
    tm.global_percentage_speed_difference(40.0)

    ego = None
    npcs = []

    log_path = PROJECT_ROOT / args.log
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ego = spawn_ego(world)

        # Spawn traffic after ego, so the ego spawn is clean.
        npcs = spawn_npc_vehicles(client, world, tm, count=args.npc)

        for _ in range(20):
            world.tick()

        ego.set_autopilot(True, tm.get_port())

        tm.ignore_lights_percentage(ego, 0.0)
        tm.ignore_signs_percentage(ego, 0.0)
        tm.ignore_vehicles_percentage(ego, 0.0)
        tm.ignore_walkers_percentage(ego, 0.0)
        tm.distance_to_leading_vehicle(ego, 6.0)
        tm.vehicle_percentage_speed_difference(ego, 45.0)

        perception = PerceptionAgent()
        planner = PlanningAgent()
        critic = SafetyCriticAgent()
        executor = ExecutionAgent(tm, ego)

        start = time.time()
        frame = 0
        total_risk = 0.0
        interventions = 0

        with open(log_path, "w", encoding="utf-8") as f:
            while time.time() - start < args.seconds:
                world.tick()
                follow_camera(world, ego)

                scene = perception.observe(world, ego)
                scene = planner.propose(scene)
                scene = critic.evaluate(scene)
                scene = executor.apply(scene)

                draw_hazards(world, scene)

                if scene["proposal"]["action"] != "continue":
                    interventions += 1

                total_risk += scene["risk"]["score"]

                trace = {
                    "frame": frame,
                    "time_s": frame * settings.fixed_delta_seconds,
                    "ego": scene["ego"],
                    "hazards": scene["hazards"][:8],
                    "proposal": scene["proposal"],
                    "risk": scene["risk"],
                    "control": scene["control"],
                    "num_hazards": len(scene["hazards"]),
                }

                f.write(json.dumps(trace) + "\n")

                if frame % 20 == 0:
                    print(
                        f"[{frame:04d}] "
                        f"action={scene['proposal']['action']} "
                        f"risk={scene['risk']['score']:.2f} "
                        f"speed={speed_mps(ego):.2f} "
                        f"hazards={len(scene['hazards'])} "
                        f"mode={scene['control']['mode']} "
                        f"reason={scene['proposal']['reason']}"
                    )

                frame += 1

        avg_risk = total_risk / max(frame, 1)

        print("\nSafeRoute TM rollout complete.")
        print(f"Frames: {frame}")
        print(f"Average risk: {avg_risk:.3f}")
        print(f"Intervention frames: {interventions}")
        print(f"Saved trace to: {log_path}")

    finally:
        if ego is not None:
            ego.set_autopilot(False)
            ego.destroy()

        for actor in npcs:
            if actor is not None:
                actor.destroy()

        world.apply_settings(original_settings)
        tm.set_synchronous_mode(False)


if __name__ == "__main__":
    main()