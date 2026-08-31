from __future__ import annotations

from .schemas import ActionEvidence, DeltaBundle, TypedEvent, evidence_id


class EventExtractor:
    def extract(self, action: ActionEvidence, delta: DeltaBundle) -> tuple[TypedEvent, ...]:
        events = []
        base_parents = (action.action_id, delta.delta_id)
        if delta.changed_cells:
            events.append(self._event("frame_changed", {"cells": len(delta.changed_cells)}, base_parents, delta))
        for payload in delta.object_events:
            events.append(self._event(str(payload["kind"]), payload, base_parents, delta))
        for payload in delta.topology_events:
            events.append(self._event(str(payload["kind"]), payload, base_parents, delta))
        if delta.score_delta > 0 or delta.level_delta > 0:
            events.append(self._event("reward", {"score_delta": delta.score_delta, "level_delta": delta.level_delta}, base_parents, delta, 1.0))
        if not events:
            events.append(self._event("no_observed_effect", {}, base_parents, delta, 0.9))
        return tuple(events)

    @staticmethod
    def _event(kind, payload, parents, delta, confidence=0.75):
        body = {"type": kind, "payload": dict(payload), "dependency_group": delta.dependency_group}
        return TypedEvent(evidence_id("event", body, parents), kind, dict(payload), tuple(parents), confidence, delta.dependency_group)
