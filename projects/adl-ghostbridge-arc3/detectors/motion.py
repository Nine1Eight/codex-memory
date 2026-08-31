from __future__ import annotations

from dataclasses import dataclass

from .base import Detection
from world.state import WorldState


@dataclass(slots=True)
class MotionDetector:
    name: str = "motion"

    def detect(self, world: WorldState, previous: WorldState | None = None) -> list[Detection]:
        if previous is None:
            return []
        moved = sum(1 for y, row in enumerate(world.frame) for x, v in enumerate(row) if y < len(previous.frame) and x < len(previous.frame[y]) and previous.frame[y][x] != v)
        return [Detection(self.name, "motion_pixels", {"changed": moved}, 0.5 if moved else 0.2, "diff")]

