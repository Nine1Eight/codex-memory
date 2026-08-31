from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .schemas import PredictionAssessment, TypedEvent, evidence_id


@dataclass(slots=True)
class TwinEffect:
    trials: int = 0
    event_groups: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    errors: list[float] = field(default_factory=list)

    def probability(self, event_type: str) -> float:
        groups = len(self.event_groups.get(event_type, set()))
        return (groups + 1.0) / (self.trials + 2.0)


class EnvironmentTwinV5:
    def __init__(self) -> None:
        self.effects: dict[tuple[str, str], TwinEffect] = defaultdict(TwinEffect)

    def predict(self, context: str, action: str) -> dict[str, Any]:
        stats = self.effects[(context, action)]
        probabilities = {kind: stats.probability(kind) for kind in stats.event_groups}
        return {"context": context, "action": action, "event_probabilities": probabilities, "trials": stats.trials, "confidence": stats.trials / (stats.trials + 3.0)}

    def assess(self, prediction: dict[str, Any], events: tuple[TypedEvent, ...]) -> PredictionAssessment:
        expected = {kind for kind, probability in prediction.get("event_probabilities", {}).items() if probability >= 0.5}
        observed = {event.event_type for event in events}
        union = expected | observed
        error = 0.0 if not union else 1.0 - len(expected & observed) / len(union)
        parents = tuple(event.event_id for event in events)
        payload = {"prediction": prediction, "observed": sorted(observed), "error": error}
        return PredictionAssessment(evidence_id("prediction", payload, parents), error, tuple(sorted(expected & observed)), tuple(sorted(expected - observed)), parents)

    def update(self, context: str, action: str, events: tuple[TypedEvent, ...], assessment: PredictionAssessment) -> None:
        stats = self.effects[(context, action)]
        stats.trials += 1
        for event in events:
            stats.event_groups[event.event_type].add(event.dependency_group)
        stats.errors.append(assessment.error)
        del stats.errors[:-64]

