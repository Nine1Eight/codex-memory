from __future__ import annotations

from dataclasses import dataclass

from .base import Detection
from world.map import connected_components, normalize_grid
from world.state import WorldState


@dataclass(slots=True)
class ConnectedComponentsDetector:
    name: str = "connected_components"

    def detect(self, world: WorldState, previous: WorldState | None = None) -> list[Detection]:
        grid = normalize_grid(world.frame)
        comps = connected_components(grid)
        return [Detection(self.name, "components", {"count": len(comps), "sizes": [len(c.cells) for c in comps[:16]]}, 0.8, "grid")]

