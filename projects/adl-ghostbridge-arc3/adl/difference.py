from __future__ import annotations

from world.state import ChangeKind, EntityChange, WorldDelta, WorldState, entity_record


class DifferenceEngine:
    def diff(self, before: WorldState, after: WorldState) -> WorldDelta:
        frame_changes = tuple(self._frame_diff(before, after))
        old = before.entity_by_id(); new = after.entity_by_id(); changes: list[EntityChange] = []
        for entity_id in sorted(old.keys() | new.keys()):
            if entity_id not in old:
                changes.append(EntityChange(ChangeKind.APPEARED, entity_id, None, entity_record(new[entity_id]), new[entity_id].confidence, (after.state_key, "entity_tracking")))
            elif entity_id not in new:
                changes.append(EntityChange(ChangeKind.DISAPPEARED, entity_id, entity_record(old[entity_id]), None, old[entity_id].confidence, (before.state_key, "entity_tracking")))
            elif old[entity_id].position != new[entity_id].position:
                changes.append(EntityChange(ChangeKind.MOVED, entity_id, entity_record(old[entity_id]), entity_record(new[entity_id]), min(old[entity_id].confidence, new[entity_id].confidence), (before.state_key, after.state_key)))
            elif old[entity_id].signature != new[entity_id].signature:
                changes.append(EntityChange(ChangeKind.MODIFIED, entity_id, entity_record(old[entity_id]), entity_record(new[entity_id]), min(old[entity_id].confidence, new[entity_id].confidence), (before.state_key, after.state_key)))
        topology = {key: (before.topology.get(key), after.topology.get(key)) for key in before.topology.keys() | after.topology.keys() if before.topology.get(key) != after.topology.get(key)}
        progress = after.progress - before.progress
        outcome = "progress" if progress > 0 or after.level > before.level else "failure" if after.failed else "changed" if frame_changes else "no_impact"
        return WorldDelta(frame_changes, changes, topology, (tuple(a.action_id for a in before.available_actions), tuple(a.action_id for a in after.available_actions)), progress, bool(topology), provenance=(before.state_key, after.state_key), outcome=outcome)

    @staticmethod
    def _frame_diff(before, after):
        height = max(before.height, after.height); width = max(before.width, after.width)
        for y in range(height):
            for x in range(width):
                old = before.frame[y][x] if y < before.height and x < len(before.frame[y]) else None
                new = after.frame[y][x] if y < after.height and x < len(after.frame[y]) else None
                if old != new: yield (x, y, old, new)
