from __future__ import annotations

from autopass_gen.core.schema import ScenarioSpec


class CarlaAdapter:
    """Boundary layer for real CARLA integration.

    The rest of the prototype is intentionally simulator-agnostic. Replace the methods below with
    CARLA client calls once the team starts running the server locally.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 2000):
        self.host = host
        self.port = port
        self.client = None

    def connect(self):
        try:
            import carla  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "CARLA Python API is not installed in this environment. Install the matching CARLA egg "
                "and run this adapter on the machine with CARLA installed."
            ) from exc
        self.client = carla.Client(self.host, self.port)
        self.client.set_timeout(10.0)
        return self.client

    def instantiate(self, spec: ScenarioSpec):
        raise NotImplementedError(
            "Implement: load town, spawn ego/lead/rear/oncoming actors, set weather, attach RGB/depth."
        )

    def tick_and_read_state(self):
        raise NotImplementedError(
            "Implement: world.tick(), sensor callbacks, actor transforms/velocities."
        )

    def apply_decision(self, decision: str):
        raise NotImplementedError(
            "Implement: BasicAgent/LaneChange/local planner control commands."
        )
