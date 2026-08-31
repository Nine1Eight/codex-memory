from __future__ import annotations

from dataclasses import dataclass

from .base import Detection
from world.map import grid_shape, normalize_grid
from world.state import WorldState


@dataclass(slots=True)
class GridDetector:
    name: str = "grid"

    def detect(self, world: WorldState, previous: WorldState | None = None) -> list[Detection]:
        grid = normalize_grid(world.frame)
        width, height = grid_shape(grid)
        return [Detection(self.name, "grid_shape", {"width": width, "height": height}, 0.95 if width and height else 0.1, "grid")]

