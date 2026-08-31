from __future__ import annotations

from collections import Counter

from .schemas import DeltaBundle, ImmutableObservation, evidence_id


class HierarchicalDifferenceEngine:
    def __init__(self, expensive_cell_threshold: int = 12) -> None:
        self.expensive_cell_threshold = expensive_cell_threshold

    def diff(self, before: ImmutableObservation, after: ImmutableObservation, force_expensive: bool = False) -> DeltaBundle:
        changed = []
        height = max(len(before.frame), len(after.frame))
        width = max(max((len(r) for r in before.frame), default=0), max((len(r) for r in after.frame), default=0))
        for y in range(height):
            for x in range(width):
                old = before.frame[y][x] if y < len(before.frame) and x < len(before.frame[y]) else None
                new = after.frame[y][x] if y < len(after.frame) and x < len(after.frame[y]) else None
                if old != new:
                    changed.append((x, y, old, new))
        score_delta = after.score - before.score
        level_delta = after.level - before.level
        expensive = force_expensive or bool(score_delta or level_delta or len(changed) >= self.expensive_cell_threshold)
        object_events = self._objects(changed) if expensive else ()
        topology_events = self._topology(before, after, changed) if expensive else ()
        dependency = evidence_id("dependency", {"pre": before.observation_id, "post": after.observation_id})
        payload = {"pre": before.observation_id, "post": after.observation_id, "changed": changed, "objects": object_events, "topology": topology_events, "score_delta": score_delta, "level_delta": level_delta, "dependency": dependency, "resolution": "hierarchical" if expensive else "cheap"}
        return DeltaBundle(evidence_id("delta", payload, (before.observation_id, after.observation_id)), before.observation_id, after.observation_id, tuple(changed), tuple(object_events), tuple(topology_events), score_delta, level_delta, dependency, payload["resolution"])

    @staticmethod
    def _objects(changed):
        removed = Counter(old for _, _, old, new in changed if old is not None and old != new)
        added = Counter(new for _, _, old, new in changed if new is not None and old != new)
        events = []
        for color in sorted(set(removed) | set(added)):
            kind = "moved_or_transformed" if removed[color] and added[color] else "appeared" if added[color] else "disappeared"
            events.append({"kind": kind, "color": color, "removed": removed[color], "added": added[color]})
        return tuple(events)

    @staticmethod
    def _topology(before, after, changed):
        if not changed:
            return ()
        before_open = sum(v == 0 for row in before.frame for v in row)
        after_open = sum(v == 0 for row in after.frame for v in row)
        return ({"kind": "reachability_candidate", "open_cell_delta": after_open - before_open},)

