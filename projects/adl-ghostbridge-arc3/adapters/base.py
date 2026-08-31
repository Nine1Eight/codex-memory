from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from world.state import Action, Frame, freeze_frame


class RuntimeBoundaryError(RuntimeError):
    """The real ARC runtime is missing or returned an invalid contract."""


@dataclass(slots=True)
class Observation:
    frame: Frame
    available_actions: tuple[Action, ...]
    game_id: str
    version: str = ""
    level: int = 0
    progress: float = 0.0
    terminal: bool = False
    level_complete: bool = False
    game_complete: bool = False
    failed: bool = False
    raw_state: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.frame = freeze_frame(self.frame)
        if not self.frame:
            raise RuntimeBoundaryError("ARC observation has no frame")
        if not self.available_actions and not self.terminal:
            raise RuntimeBoundaryError("active ARC observation has no available actions")


class GameSession(Protocol):
    game_id: str

    def first_observation(self) -> Observation: ...
    def execute(self, action: Action) -> Observation: ...
    def reset_level(self) -> Observation: ...
    def close(self) -> None: ...


class RuntimeAdapter(Protocol):
    def game_ids(self) -> Sequence[str]: ...
    def open_game_once(self, game_id: str) -> GameSession: ...
