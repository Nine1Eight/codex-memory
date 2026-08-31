from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .schemas import ImmutableObservation, canonical


@dataclass(frozen=True, slots=True)
class TrackedObject:
    object_id: str
    color: int
    cells: tuple[tuple[int, int], ...]
    parent_ids: tuple[str, ...] = ()


class PersistentObjectTracker:
    def __init__(self) -> None:
        self.previous: dict[str, tuple[TrackedObject, ...]] = {}

    @staticmethod
    def _components(observation: ImmutableObservation) -> list[tuple[int, tuple[tuple[int, int], ...]]]:
        frame = observation.frame; seen = set(); output = []
        for y, row in enumerate(frame):
            for x, color in enumerate(row):
                if color == 0 or (x, y) in seen: continue
                stack = [(x, y)]; seen.add((x, y)); cells = []
                while stack:
                    cx, cy = stack.pop(); cells.append((cx, cy))
                    for nx, ny in ((cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)):
                        if 0 <= ny < len(frame) and 0 <= nx < len(frame[ny]) and (nx,ny) not in seen and frame[ny][nx] == color:
                            seen.add((nx,ny)); stack.append((nx,ny))
                output.append((color, tuple(sorted(cells))))
        return output

    def update(self, observation: ImmutableObservation) -> tuple[TrackedObject, ...]:
        prior = self.previous.get(observation.game_id, ())
        unmatched = list(prior); tracked = []
        for color, cells in self._components(observation):
            candidates = [item for item in unmatched if item.color == color]
            if candidates:
                match = min(candidates, key=lambda item: abs(len(item.cells)-len(cells)) + len(set(item.cells)^set(cells)))
                unmatched.remove(match); oid = match.object_id; parents = (match.object_id,)
            else:
                oid = "obj-" + sha256(canonical((observation.game_id, color, cells)).encode()).hexdigest()[:16]; parents = ()
            tracked.append(TrackedObject(oid, color, cells, parents))
        result = tuple(tracked); self.previous[observation.game_id] = result
        return result

