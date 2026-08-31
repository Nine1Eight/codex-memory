from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Iterable, Sequence

from .base import GameSession, Observation, RuntimeAdapter, RuntimeBoundaryError
from world.state import Action, freeze_frame


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def frame_from_runtime(frame: Any) -> tuple[tuple[int, ...], ...]:
    for name in ("frame", "data", "pixels", "observation"):
        candidate = getattr(frame, name, None)
        if candidate is not None:
            if isinstance(candidate, (list, tuple)) and len(candidate) == 1:
                candidate = candidate[0]
            if hasattr(candidate, "tolist"):
                candidate = candidate.tolist()
            try:
                return freeze_frame(candidate)
            except (TypeError, ValueError):
                continue
    raise RuntimeBoundaryError(f"cannot extract grid frame from {type(frame).__name__}")


def action_ids(frame: Any) -> tuple[int, ...]:
    result: list[int] = []
    for item in getattr(frame, "available_actions", ()) or ():
        raw = _value(item)
        try:
            result.append(int(raw))
        except (TypeError, ValueError):
            continue
    return tuple(sorted(set(result)))


def normalize_frame(frame: Any, game_id: str, previous_level: int = 0) -> Observation:
    state = str(getattr(_value(getattr(frame, "state", "")), "name", _value(getattr(frame, "state", "")))).lower()
    level = int(getattr(frame, "levels_completed", previous_level) or 0)
    win_levels = int(getattr(frame, "win_levels", 0) or 0)
    terminal = state.endswith("win") or "game_over" in state or state.endswith("lost")
    won = state.endswith("win")
    ids = action_ids(frame)
    return Observation(
        frame=frame_from_runtime(frame),
        available_actions=tuple(Action(i) for i in ids),
        game_id=game_id,
        level=level,
        progress=float(getattr(frame, "score", level) or level),
        terminal=terminal,
        level_complete=level > previous_level,
        game_complete=won or (win_levels > 0 and level >= win_levels),
        failed=terminal and not won,
        raw_state=state,
        metadata={"win_levels": win_levels},
    )


@dataclass(slots=True)
class BoundGameSession:
    game_id: str
    game: Any
    action_builder: Callable[[Action, str], Any]
    _last: Observation | None = None
    _started: bool = False

    def _perform(self, action: Action) -> Observation:
        try:
            raw = self.game.perform_action(self.action_builder(action, self.game_id), raw=True)
        except TypeError:
            raw = self.game.perform_action(self.action_builder(action, self.game_id))
        previous = self._last.level if self._last else 0
        self._last = normalize_frame(raw, self.game_id, previous)
        return self._last

    def first_observation(self) -> Observation:
        if self._started:
            raise RuntimeBoundaryError("first_observation called more than once")
        self._started = True
        return self._perform(Action(0, name="RESET"))

    def execute(self, action: Action) -> Observation:
        if not self._started:
            raise RuntimeBoundaryError("execute called before first_observation")
        if action.action_id == 0:
            raise RuntimeBoundaryError("reset must use reset_level, not execute")
        return self._perform(action)

    def reset_level(self) -> Observation:
        return self._perform(Action(0, name="RESET"))

    def close(self) -> None:
        closer = getattr(self.game, "close", None)
        if callable(closer):
            closer()


@dataclass(slots=True)
class BoundRuntimeAdapter(RuntimeAdapter):
    """Binds production logic to official/local ARC objects without importing Kaggle-only wheels."""

    factories: dict[str, Callable[[], Any]]
    action_builder: Callable[[Action, str], Any]
    _opened: set[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._opened = set()

    def game_ids(self) -> Sequence[str]:
        return tuple(sorted(self.factories))

    def open_game_once(self, game_id: str) -> GameSession:
        if game_id in self._opened:
            raise RuntimeBoundaryError(f"single-environment contract violated for {game_id}")
        if game_id not in self.factories:
            raise RuntimeBoundaryError(f"unknown game_id {game_id}")
        self._opened.add(game_id)
        return BoundGameSession(game_id, self.factories[game_id](), self.action_builder)
