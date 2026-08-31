from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .sid import SemanticPrior
from world.state import Reflection, clamp01


@dataclass(slots=True)
class DetectorProfile:
    name: str
    confidence: float
    stability: float
    action_relevance: float
    information_gain: float
    score_relevance: float
    compute_cost: float
    failure_history: float = 0.0
    redundancy: float = 0.0
    active: bool = True

    def rank(self, prior: float = 0.0) -> float:
        benefit = 1.4 * self.confidence + self.stability + self.action_relevance + self.information_gain + self.score_relevance + prior
        return benefit - self.compute_cost - self.failure_history - self.redundancy


class AdaptivePerceptionRouter:
    CORE = ("grid", "components", "objects", "topology", "frame_difference", "motion", "player", "goal", "terminal", "novelty")

    def __init__(self) -> None:
        self.profiles = {name: DetectorProfile(name, 0.55, 0.5, 0.6, 0.5, 0.5, 0.1 if name in self.CORE[:4] else 0.25) for name in self.CORE}

    def select(self, prior: SemanticPrior, budget: int = 7, requested: Iterable[str] = ()) -> tuple[str, ...]:
        requested_set = set(requested)
        ranked = sorted(self.profiles.values(), key=lambda p: (p.name not in requested_set, -p.rank(prior.detectors.get(p.name, 0.0))))
        chosen = [profile.name for profile in ranked if profile.active and (profile.rank(prior.detectors.get(profile.name, 0.0)) > 0 or profile.name in requested_set)][:budget]
        for required in ("grid", "components"):
            if required not in chosen:
                chosen.insert(0, required)
        return tuple(dict.fromkeys(chosen))

    def update(self, reflection: Reflection) -> None:
        direction = 0.04 if reflection.prediction_error < 0.25 else -0.06
        for name in reflection.prediction.basis:
            if name in self.profiles:
                profile = self.profiles[name]
                profile.confidence = clamp01(profile.confidence + direction)
                profile.failure_history = clamp01(profile.failure_history + (0.03 if direction < 0 else -0.02))

    def activate(self, name: str) -> None:
        self.profiles.setdefault(name, DetectorProfile(name, 0.4, 0.3, 0.5, 0.7, 0.5, 0.4)).active = True

    def deactivate(self, name: str) -> None:
        if name in self.profiles and name not in {"grid", "components"}:
            self.profiles[name].active = False
