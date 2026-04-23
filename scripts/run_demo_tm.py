import argparse
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


def spawn_ego(world):
    bp_lib = world.get_blueprint_library()
    bp = bp_lib.filter("vehicle.tesla.model3")[0]
    bp.set_attribute("role_name", "hero")

    spawn_points = world.get_map().get_spawn_points()

    # Use safer spawn points away from walls/intersections as much as possible.
    random.shuffle(spawn_points)

    for sp in spawn_points:
        vehicle = world.try_spawn_actor(bp, sp)
        if vehicle is not None:
            return vehicle

    raise RuntimeError("Could not spawn ego vehicle.")


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


def speed_mps(vehicle):
    v = vehicle.get_velocity()
    return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--seconds", type=float, default=45.0)
    parser.add_argument("--town", default=None)
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
    tm.set_global_distance_to_leading_vehicle(4.0)
    tm.global_percentage_speed_difference(45.0)  # slower than speed limit

    ego = None

    try:
        ego = spawn_ego(world)

        # Let physics settle.
        for _ in range(20):
            world.tick()

        # Traffic Manager is much more stable than custom BehaviorAgent routing for baseline demos.
        ego.set_autopilot(True, tm.get_port())

        # Conservative driving behavior.
        tm.ignore_lights_percentage(ego, 0.0)
        tm.ignore_signs_percentage(ego, 0.0)
        tm.ignore_vehicles_percentage(ego, 0.0)
        tm.ignore_walkers_percentage(ego, 0.0)
        tm.distance_to_leading_vehicle(ego, 5.0)
        tm.vehicle_percentage_speed_difference(ego, 50.0)

        start = time.time()
        frame = 0

        while time.time() - start < args.seconds:
            world.tick()
            follow_camera(world, ego)

            if frame % 20 == 0:
                control = ego.get_control()
                print(
                    f"[{frame:04d}] "
                    f"speed={speed_mps(ego):.2f} "
                    f"throttle={control.throttle:.2f} "
                    f"brake={control.brake:.2f} "
                    f"steer={control.steer:.2f}"
                )

            frame += 1

    finally:
        if ego is not None:
            ego.set_autopilot(False)
            ego.destroy()

        world.apply_settings(original_settings)
        tm.set_synchronous_mode(False)


if __name__ == "__main__":
    main()