from __future__ import annotations

from dataclasses import dataclass

from .base import Detection
from world.state import WorldState


@dataclass(slots=True)
class FrameDeltaDetector:
    name: str = "frame_delta"

    def detect(self, world: WorldState, previous: WorldState | None = None) -> list[Detection]:
        if previous is None:
            return [Detection(self.name, "initial_frame", {"hash": world.frame_hash}, 0.4, "frame")]
        changed = world.frame_hash != previous.frame_hash or world.frame != previous.frame
        return [Detection(self.name, "frame_changed" if changed else "frame_stable", {"changed": changed}, 0.9 if changed else 0.6, "frame")]

