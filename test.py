import carla

client = carla.Client("localhost", 2000)
client.set_timeout(5.0)

world = client.get_world()
print(world.get_map().name)
