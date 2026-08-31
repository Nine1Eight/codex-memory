from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import ImmutableObservation


@dataclass(slots=True)
class PendingAction:
    game_id: str
    step: int
    pre: ImmutableObservation
    action: Any
    deadline_tick: int
    observations: list[ImmutableObservation] = field(default_factory=list)


class TemporalOwnership:
    def __init__(self, stable_frames: int = 2, deadline_frames: int = 8) -> None:
        self.stable_frames = max(1, stable_frames)
        self.deadline_frames = max(self.stable_frames, deadline_frames)
        self.pending: dict[str, PendingAction] = {}

    def begin(self, game_id: str, step: int, pre: ImmutableObservation, action: Any) -> PendingAction:
        if game_id in self.pending:
            raise RuntimeError(f"action still pending for {game_id}")
        item = PendingAction(game_id, step, pre, action, step + self.deadline_frames)
        self.pending[game_id] = item
        return item

    def observe(self, game_id: str, observation: ImmutableObservation, authoritative: bool = False) -> bool:
        item = self.pending[game_id]
        item.observations.append(observation)
        recent = item.observations[-self.stable_frames:]
        stable = len(recent) >= self.stable_frames and len({x.frame_hash for x in recent}) == 1
        expired = authoritative or len(item.observations) >= self.deadline_frames or observation.terminal
        return stable or expired

    def settle(self, game_id: str) -> tuple[ImmutableObservation, tuple[str, ...]]:
        item = self.pending.pop(game_id)
        if not item.observations:
            raise RuntimeError("cannot settle action without post observation")
        return item.observations[-1], tuple(x.observation_id for x in item.observations)
