from __future__ import annotations

from collections import Counter
from hashlib import sha1
from typing import Iterable

from adapters.base import Observation
from world.map import connected_components, dominant_color, normalize_grid
from world.state import DetectorEvidence, Entity, GameFingerprint, GameIdentity, WorldState
from world.topology import infer_walkability


class PerceptionEngine:
    """Pure-Python detector ensemble producing compact normalized states."""

    def process(self, observation: Observation, detectors: Iterable[str], previous: WorldState | None = None) -> WorldState:
        active = set(detectors)
        grid = normalize_grid(observation.frame)
        components = connected_components(grid)
        background = dominant_color(grid)
        evidence: list[DetectorEvidence] = []
        if "grid" in active:
            evidence.append(DetectorEvidence("grid", "shape", {"width": len(grid[0]), "height": len(grid), "palette": sorted({v for r in grid for v in r})}, 1.0, ("raw_frame",), observation.level))
        if "components" in active:
            evidence.append(DetectorEvidence("components", "regions", {"count": len(components), "sizes": [len(c.cells) for c in components]}, 0.9, ("raw_frame",), observation.level))

        prior_entities = previous.entities if previous else []
        entities = self._track_entities(components, prior_entities)
        self._infer_roles(entities, previous)
        player = max((e for e in entities if e.kind == "player"), key=lambda e: e.confidence, default=None)
        free, blocked, topology = infer_walkability(grid, player.position if player else None)
        if "topology" in active:
            evidence.append(DetectorEvidence("topology", "walkability", topology, 0.65 if player else 0.45, ("raw_frame", "dominant_color"), observation.level))
        if previous and ("frame_difference" in active or "motion" in active):
            changes = self._frame_changes(previous.frame, grid)
            evidence.append(DetectorEvidence("frame_difference", "changed_cells", {"count": len(changes), "sample": changes[:32]}, 0.95, (previous.state_key, "raw_frame"), observation.level))
        if "objects" in active:
            evidence.append(DetectorEvidence("objects", "tracked_entities", {"count": len(entities), "ids": [e.entity_id for e in entities]}, 0.75, ("components",), observation.level))
        if "novelty" in active:
            digest = sha1(repr(grid).encode()).hexdigest()[:16]
            evidence.append(DetectorEvidence("novelty", "frame_hash", {"digest": digest, "novel": previous is None or grid != previous.frame}, 0.9, ("raw_frame",), observation.level))

        fingerprint = GameFingerprint.from_observation(grid, (a.action_id for a in observation.available_actions), (len(c.cells) for c in components))
        confidence = sum(e.confidence for e in evidence) / max(1, len(evidence))
        return WorldState(
            identity=GameIdentity.parse(observation.game_id, observation.version), frame=grid,
            available_actions=observation.available_actions, level=observation.level,
            step=(previous.step + 1 if previous else 0), entities=entities,
            geometry={"width": len(grid[0]), "height": len(grid), "background": background},
            topology=topology, free_space=free, collision=blocked,
            temporal_state={"raw_state": observation.raw_state}, progress=observation.progress,
            confidence=confidence, uncertainty={"player": 0.2 if player else 1.0, "goal": 0.8},
            provenance={"frame": ("runtime_observation",), "entities": ("connected_components",), "topology": ("dominant_color",)},
            evidence=evidence, terminal=observation.terminal, level_complete=observation.level_complete,
            game_complete=observation.game_complete, failed=observation.failed, fingerprint=fingerprint,
        )

    @staticmethod
    def _frame_changes(before, after):
        height = max(len(before), len(after)); width = max(max((len(r) for r in before), default=0), max((len(r) for r in after), default=0))
        changes = []
        for y in range(height):
            for x in range(width):
                old = before[y][x] if y < len(before) and x < len(before[y]) else None
                new = after[y][x] if y < len(after) and x < len(after[y]) else None
                if old != new: changes.append((x, y, old, new))
        return changes

    def _track_entities(self, components, previous):
        unused = set(e.entity_id for e in previous)
        old = {e.entity_id: e for e in previous}
        output = []
        next_id = 0
        for component in components:
            matches = [(self._match_score(component, entity), entity) for entity in previous if entity.entity_id in unused and entity.color == component.color]
            score, match = max(matches, default=(0.0, None), key=lambda row: row[0])
            if match is not None and score >= 0.35:
                entity_id = match.entity_id; unused.remove(entity_id); kind = match.kind
            else:
                while f"entity-{next_id}" in old: next_id += 1
                entity_id = f"entity-{next_id}"; next_id += 1; kind = "object"
            output.append(Entity(entity_id, kind, component.cells, component.color, confidence=max(0.55, score), provenance=("connected_components",)))
        return output

    @staticmethod
    def _match_score(component, entity):
        size_ratio = min(len(component.cells), len(entity.cells)) / max(len(component.cells), len(entity.cells))
        cx = sum(x for x, _ in component.cells) / len(component.cells); cy = sum(y for _, y in component.cells) / len(component.cells)
        distance = abs(cx - entity.position[0]) + abs(cy - entity.position[1])
        return 0.65 * size_ratio + 0.35 / (1 + distance)

    @staticmethod
    def _infer_roles(entities, previous):
        if previous:
            old = previous.entity_by_id()
            moved = [e for e in entities if e.entity_id in old and e.position != old[e.entity_id].position]
            if len(moved) == 1:
                moved[0].kind = "player"; moved[0].confidence = max(moved[0].confidence, 0.85); return
        if entities:
            smallest = min(entities, key=lambda e: (len(e.cells), e.entity_id))
            smallest.kind = "player_candidate"; smallest.confidence = min(smallest.confidence, 0.45)
