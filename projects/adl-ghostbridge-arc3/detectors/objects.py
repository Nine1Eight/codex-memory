from __future__ import annotations

from dataclasses import dataclass

from .base import Detection
from world.map import normalize_grid
from world.state import WorldState


@dataclass(slots=True)
class ObjectDetector:
    name: str = "objects"

    def detect(self, world: WorldState, previous: WorldState | None = None) -> list[Detection]:
        grid = normalize_grid(world.frame)
        nonzero = [(x, y, v) for y, row in enumerate(grid) for x, v in enumerate(row) if v != 0]
        return [Detection(self.name, "objects", {"count": len(nonzero), "sample": nonzero[:8]}, 0.7 if nonzero else 0.1, "grid")]

