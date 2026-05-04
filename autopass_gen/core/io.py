from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autopass_gen.core.schema import ScenarioSpec


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def load_scenario(path: str | Path) -> ScenarioSpec:
    return ScenarioSpec.model_validate(load_json(path))


def save_scenario(spec: ScenarioSpec, path: str | Path) -> None:
    save_json(spec, path)
