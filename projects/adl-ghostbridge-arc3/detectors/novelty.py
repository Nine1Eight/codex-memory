from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from .base import Detection
from world.state import WorldState


@dataclass(slots=True)
class NoveltyDetector:
    name: str = "novelty"

    def detect(self, world: WorldState, previous: WorldState | None = None) -> list[Detection]:
        h = sha1(repr(world.frame).encode("utf-8")).hexdigest()
        novelty = 1.0 if previous is None or h != previous.frame_hash else 0.0
        return [Detection(self.name, "novelty", {"novelty": novelty}, novelty, "hash")]

