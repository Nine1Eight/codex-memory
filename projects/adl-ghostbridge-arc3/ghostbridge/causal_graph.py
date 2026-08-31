from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .schemas import ActionEvidence, TypedEvent


@dataclass(slots=True)
class CausalBelief:
    cause: str
    effect: str
    context: str
    support_groups: set[str] = field(default_factory=set)
    contradiction_groups: set[str] = field(default_factory=set)
    evidence_ids: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        # Correlated pixel/object/topology views share a dependency group and count once.
        support = len(self.support_groups)
        contradictions = len(self.contradiction_groups)
        return (support + 1.0) / (support + contradictions + 3.0)


class CalibratedCausalGraph:
    def __init__(self) -> None:
        self.beliefs: dict[tuple[str, str, str], CausalBelief] = {}
        self.chains: dict[str, list[tuple[str, str]]] = defaultdict(list)

    def update(self, action: ActionEvidence, events: tuple[TypedEvent, ...], context: str) -> tuple[str, ...]:
        updated = []
        cause = f"action:{action.action}:{dict(action.data)}"
        grouped: dict[str, list[TypedEvent]] = defaultdict(list)
        for event in events:
            grouped[event.dependency_group].append(event)
        for dependency_group, correlated in grouped.items():
            effects = {event.event_type for event in correlated}
            for effect in effects:
                key = (cause, effect, context)
                belief = self.beliefs.setdefault(key, CausalBelief(cause, effect, context))
                if effect == "no_observed_effect":
                    belief.contradiction_groups.add(dependency_group)
                else:
                    belief.support_groups.add(dependency_group)
                belief.evidence_ids.extend(event.event_id for event in correlated if event.event_type == effect)
                updated.extend(event.event_id for event in correlated if event.event_type == effect)
            self.chains[context].append((cause, "+".join(sorted(effects))))
        return tuple(dict.fromkeys(updated))

    def effects_for(self, action: str, context: str, threshold: float = 0.45) -> tuple[CausalBelief, ...]:
        return tuple(
            belief for (cause, _, candidate_context), belief in self.beliefs.items()
            if cause.startswith(f"action:{action}:") and candidate_context == context and belief.confidence >= threshold
        )

