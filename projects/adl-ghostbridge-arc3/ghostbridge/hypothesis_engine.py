from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from .schemas import TypedEvent, canonical


@dataclass(slots=True)
class MechanicHypothesis:
    hypothesis_id: str
    claim: str
    predicted_events: frozenset[str]
    context: str
    support_groups: set[str] = field(default_factory=set)
    contradiction_groups: set[str] = field(default_factory=set)
    evidence_ids: list[str] = field(default_factory=list)
    active: bool = True

    @property
    def confidence(self) -> float:
        s, c = len(self.support_groups), len(self.contradiction_groups)
        return (s + 1.0) / (s + c + 3.0)


class HypothesisEngine:
    def __init__(self) -> None:
        self.hypotheses: dict[str, MechanicHypothesis] = {}

    def propose(self, claim: str, predicted_events: set[str], context: str) -> MechanicHypothesis:
        material = {"claim": claim, "events": sorted(predicted_events), "context": context}
        hid = f"hyp-{sha256(canonical(material).encode()).hexdigest()[:20]}"
        hypothesis = self.hypotheses.get(hid)
        if hypothesis is None:
            hypothesis = MechanicHypothesis(hid, claim, frozenset(predicted_events), context)
            self.hypotheses[hid] = hypothesis
        return hypothesis

    def update(self, events: tuple[TypedEvent, ...], context: str) -> tuple[dict[str, Any], ...]:
        observed = {event.event_type for event in events}
        groups = {event.dependency_group for event in events}
        output = []
        for hypothesis in self.hypotheses.values():
            if not hypothesis.active or hypothesis.context != context:
                continue
            matched = bool(hypothesis.predicted_events & observed)
            target = hypothesis.support_groups if matched else hypothesis.contradiction_groups
            target.update(groups)
            hypothesis.evidence_ids.extend(event.event_id for event in events)
            if len(hypothesis.contradiction_groups) >= 3 and hypothesis.confidence < 0.3:
                hypothesis.active = False
            output.append({"hypothesis_id": hypothesis.hypothesis_id, "supported": matched, "confidence": hypothesis.confidence, "active": hypothesis.active, "evidence_ids": tuple(event.event_id for event in events)})
        return tuple(output)

    def competing_pair(self, context: str) -> tuple[MechanicHypothesis, MechanicHypothesis] | None:
        active = sorted((h for h in self.hypotheses.values() if h.active and h.context == context), key=lambda h: (-h.confidence, h.hypothesis_id))
        for left in active:
            for right in active:
                if left.hypothesis_id < right.hypothesis_id and left.predicted_events != right.predicted_events:
                    return left, right
        return None

