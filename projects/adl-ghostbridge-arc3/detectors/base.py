from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from world.state import WorldState


@dataclass(slots=True)
class Detection:
    detector: str
    label: str
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    provenance: str = "unknown"


@dataclass(slots=True)
class DetectorMetrics:
    structural_confidence: float = 0.0
    temporal_consistency: float = 0.0
    action_relevance: float = 0.0
    information_gain: float = 0.0
    reward_relevance: float = 0.0
    learned_game_prior: float = 0.0
    compute_cost: float = 0.0
    failure_penalty: float = 0.0
    redundancy: float = 0.0

    def score(self) -> float:
        return (
            self.structural_confidence
            + self.temporal_consistency
            + self.action_relevance
            + self.information_gain
            + self.reward_relevance
            + self.learned_game_prior
            - self.compute_cost
            - self.failure_penalty
            - self.redundancy
        )


@dataclass(slots=True)
class DetectorEvidence:
    detection: Detection
    metrics: DetectorMetrics


@dataclass(slots=True)
class DetectorProfile:
    name: str
    metrics: DetectorMetrics = field(default_factory=DetectorMetrics)
    enabled: bool = True


class Detector(Protocol):
    name: str

    def detect(self, world: WorldState, previous: WorldState | None = None) -> list[Detection]:
        ...

