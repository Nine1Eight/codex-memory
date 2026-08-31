from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from .schemas import TransitionEnvelope


@dataclass(frozen=True, slots=True)
class RewardCredit:
    transition_id: str
    reward_transition_id: str
    credit: float
    distance: int
    evidence_ids: tuple[str, ...]


class RewardPathModel:
    def __init__(self, horizon: int = 12) -> None:
        self.horizon = horizon
        self.history: dict[str, deque[TransitionEnvelope]] = defaultdict(lambda: deque(maxlen=horizon))
        self.credits: dict[str, float] = defaultdict(float)
        self.verified_paths: dict[str, list[tuple[str, ...]]] = defaultdict(list)

    def attribute(self, envelope: TransitionEnvelope) -> tuple[dict[str, Any], ...]:
        history = self.history[envelope.game_id]
        output = []
        reward = envelope.delta.score_delta + max(0, envelope.delta.level_delta)
        if reward > 0:
            chain = list(history) + [envelope]
            path = tuple(item.action.action for item in chain)
            for distance, item in enumerate(reversed(chain)):
                credit = reward * (0.72 ** distance)
                self.credits[item.transition_id] += credit
                output.append({"transition_id": item.transition_id, "reward_transition_id": envelope.transition_id, "credit": credit, "distance": distance, "evidence_ids": (item.delta.delta_id, envelope.delta.delta_id)})
            if path not in self.verified_paths[envelope.game_id]:
                self.verified_paths[envelope.game_id].append(path)
        history.append(envelope)
        return tuple(output)

    def expected_additional_reward(self, game_id: str) -> float:
        paths = self.verified_paths.get(game_id, ())
        return sum(1.0 / max(1, len(path)) for path in paths)

