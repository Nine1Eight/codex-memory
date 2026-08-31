from __future__ import annotations

from dataclasses import dataclass

from .base import Detection
from world.map import normalize_grid
from world.topology import summarize_topology
from world.state import WorldState


@dataclass(slots=True)
class TopologyDetector:
    name: str = "topology"

    def detect(self, world: WorldState, previous: WorldState | None = None) -> list[Detection]:
        topo = summarize_topology(normalize_grid(world.frame))
        return [Detection(self.name, "topology", topo, 0.75, "grid")]

