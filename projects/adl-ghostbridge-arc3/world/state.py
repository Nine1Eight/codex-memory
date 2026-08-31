from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping

Coordinate = tuple[int, int]
Frame = tuple[tuple[int, ...], ...]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def freeze_frame(frame: Iterable[Iterable[int]]) -> Frame:
    return tuple(tuple(int(cell) for cell in row) for row in frame)


class ChangeKind(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    MOVED = "MOVED"
    MODIFIED = "MODIFIED"
    ACTIVATED = "ACTIVATED"
    DEACTIVATED = "DEACTIVATED"
    APPEARED = "APPEARED"
    DISAPPEARED = "DISAPPEARED"
    MERGED = "MERGED"
    SPLIT = "SPLIT"
    UNKNOWN = "UNKNOWN"


class OutcomeClass(str, Enum):
    CONFIRMED = "CONFIRMED"
    PARTIAL = "PARTIAL"
    CONTRADICTION = "CONTRADICTION"
    NOVEL = "NOVEL"
    PROGRESS = "PROGRESS"
    FAILURE = "FAILURE"


@dataclass(frozen=True, slots=True)
class GameIdentity:
    full_id: str
    base_id: str
    version: str
    prefix: str
    characters: tuple[str, ...]
    numeric_segments: tuple[int, ...]

    @classmethod
    def parse(cls, game_id: str, version: str = "") -> "GameIdentity":
        if not game_id or not str(game_id).strip():
            raise ValueError("game_id must be non-empty")
        full = str(game_id).strip()
        match = re.match(r"^(.*?)(?:[-_]?v(?:ersion)?[-_]?(\d+(?:\.\d+)*))?$", full, re.I)
        base = (match.group(1) if match else full).rstrip("-_") or full
        parsed_version = version or (match.group(2) if match and match.group(2) else "")
        prefix_match = re.match(r"[A-Za-z]+", base)
        prefix = prefix_match.group(0).lower() if prefix_match else base[:2].lower()
        return cls(full, base, parsed_version, prefix, tuple(full), tuple(int(x) for x in re.findall(r"\d+", full)))


@dataclass(frozen=True, slots=True)
class GameFingerprint:
    width: int
    height: int
    palette: tuple[int, ...]
    component_sizes: tuple[int, ...]
    available_action_ids: tuple[int, ...]
    digest: str

    @classmethod
    def from_observation(cls, frame: Frame, action_ids: Iterable[int], component_sizes: Iterable[int] = ()) -> "GameFingerprint":
        height = len(frame)
        width = max((len(row) for row in frame), default=0)
        palette = tuple(sorted({cell for row in frame for cell in row}))
        sizes = tuple(sorted((int(x) for x in component_sizes), reverse=True)[:32])
        actions = tuple(sorted({int(x) for x in action_ids}))
        raw = json.dumps([width, height, palette, sizes, actions], separators=(",", ":"))
        return cls(width, height, palette, sizes, actions, sha256(raw.encode()).hexdigest()[:24])


@dataclass(slots=True)
class DetectorEvidence:
    detector: str
    label: str
    payload: dict[str, Any]
    confidence: float
    provenance: tuple[str, ...] = ()
    step: int = 0

    def __post_init__(self) -> None:
        self.confidence = clamp01(self.confidence)


@dataclass(slots=True)
class Entity:
    entity_id: str
    kind: str
    cells: tuple[Coordinate, ...]
    color: int | None = None
    state: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.cells = tuple(sorted((int(x), int(y)) for x, y in self.cells))
        self.confidence = clamp01(self.confidence)

    @property
    def position(self) -> Coordinate:
        if not self.cells:
            return (0, 0)
        return (round(sum(x for x, _ in self.cells) / len(self.cells)), round(sum(y for _, y in self.cells) / len(self.cells)))

    @property
    def signature(self) -> tuple[Any, ...]:
        return (self.kind, self.color, len(self.cells), tuple(sorted(self.state.items())))


@dataclass(slots=True)
class Relation:
    subject: str
    predicate: str
    object: str
    confidence: float = 0.5
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Action:
    action_id: int
    data: Mapping[str, Any] = field(default_factory=dict)
    name: str = ""

    def key(self) -> str:
        return f"{self.action_id}:{json.dumps(dict(self.data), sort_keys=True, separators=(',', ':'))}"


@dataclass(slots=True)
class EntityChange:
    kind: ChangeKind
    entity_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    confidence: float
    provenance: tuple[str, ...]


@dataclass(slots=True)
class WorldDelta:
    frame_changes: tuple[tuple[int, int, int | None, int | None], ...] = ()
    entity_changes: list[EntityChange] = field(default_factory=list)
    topology_changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    action_changes: tuple[tuple[int, ...], tuple[int, ...]] = ((), ())
    progress_delta: float = 0.0
    route_changed: bool = False
    detector_changes: dict[str, float] = field(default_factory=dict)
    plan_changed: bool = False
    capability_changes: tuple[str, ...] = ()
    outcome: str = "unchanged"
    provenance: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.frame_changes or self.entity_changes or self.topology_changes or self.progress_delta or self.action_changes[0] != self.action_changes[1])

    def summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for change in self.entity_changes:
            counts[change.kind.value] = counts.get(change.kind.value, 0) + 1
        return {"frame_cells": len(self.frame_changes), "entity_changes": counts, "topology_keys": sorted(self.topology_changes), "actions_before": self.action_changes[0], "actions_after": self.action_changes[1], "progress_delta": self.progress_delta, "outcome": self.outcome}


@dataclass(slots=True)
class WorldState:
    identity: GameIdentity
    frame: Frame
    available_actions: tuple[Action, ...]
    level: int = 0
    step: int = 0
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    geometry: dict[str, Any] = field(default_factory=dict)
    topology: dict[str, Any] = field(default_factory=dict)
    free_space: frozenset[Coordinate] = frozenset()
    collision: frozenset[Coordinate] = frozenset()
    object_states: dict[str, Any] = field(default_factory=dict)
    interaction_states: dict[str, Any] = field(default_factory=dict)
    temporal_state: dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    confidence: float = 0.0
    uncertainty: dict[str, float] = field(default_factory=dict)
    provenance: dict[str, tuple[str, ...]] = field(default_factory=dict)
    evidence: list[DetectorEvidence] = field(default_factory=list)
    terminal: bool = False
    level_complete: bool = False
    game_complete: bool = False
    failed: bool = False
    fingerprint: GameFingerprint | None = None

    def __post_init__(self) -> None:
        self.frame = freeze_frame(self.frame)
        self.available_actions = tuple(self.available_actions)
        self.confidence = clamp01(self.confidence)

    @property
    def width(self) -> int:
        return max((len(row) for row in self.frame), default=0)

    @property
    def height(self) -> int:
        return len(self.frame)

    @property
    def state_key(self) -> str:
        material = {"game": self.identity.full_id, "level": self.level, "frame": self.frame, "objects": self.object_states, "interactions": self.interaction_states, "actions": [a.key() for a in self.available_actions]}
        return sha256(json.dumps(material, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()[:24]

    def entity_by_id(self) -> dict[str, Entity]:
        return {entity.entity_id: entity for entity in self.entities}

    def player(self) -> Entity | None:
        return max((e for e in self.entities if e.kind == "player"), key=lambda e: e.confidence, default=None)

    def to_dict(self, include_frame: bool = False) -> dict[str, Any]:
        result = asdict(self)
        result["identity"] = asdict(self.identity)
        result["available_actions"] = [asdict(a) for a in self.available_actions]
        result["free_space"] = sorted(self.free_space)
        result["collision"] = sorted(self.collision)
        result["state_key"] = self.state_key
        if not include_frame:
            result.pop("frame", None)
        return result


@dataclass(slots=True)
class Transition:
    source_key: str
    action: Action
    target_key: str
    delta: WorldDelta
    context: dict[str, Any] = field(default_factory=dict)
    provenance: tuple[str, ...] = ()


@dataclass(slots=True)
class CausalEdge:
    cause: str
    effect: str
    context_key: str
    support: int = 0
    contradictions: int = 0
    confidence: float = 0.0
    provenance: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Hypothesis:
    hypothesis_id: str
    claim: str
    category: str
    supporting_evidence: list[str]
    contradictions: list[str]
    confidence: float
    predicted_outcome: dict[str, Any]
    minimum_discriminating_test: tuple[Action, ...]
    estimated_action_cost: float
    estimated_failure_risk: float
    information_gain: float
    score_relevance: float
    active: bool = True

    def utility(self) -> float:
        return self.confidence * self.information_gain * self.score_relevance - self.estimated_action_cost - self.estimated_failure_risk


@dataclass(slots=True)
class Plan:
    actions: tuple[Action, ...]
    rationale: str
    expected_progress: float
    expected_failure: float
    information_gain: float
    confidence: float
    source: str
    cursor: int = 0

    def next_action(self) -> Action:
        if self.cursor >= len(self.actions):
            raise RuntimeError("plan has no remaining action")
        action = self.actions[self.cursor]
        self.cursor += 1
        return action


@dataclass(slots=True)
class Prediction:
    action: Action
    state_key: str
    preconditions: tuple[str, ...]
    expected_movement: dict[str, tuple[Coordinate, Coordinate]]
    expected_object_changes: dict[str, Any]
    expected_topology_changes: dict[str, Any]
    expected_progress: float
    expected_failure: float
    confidence: float
    basis: tuple[str, ...]


@dataclass(slots=True)
class Reflection:
    outcome: OutcomeClass
    prediction: Prediction
    actual_state_key: str
    delta: WorldDelta
    prediction_error: float
    confirmed: tuple[str, ...]
    contradicted: tuple[str, ...]
    novel: tuple[str, ...]
    score_value: float
    provenance: tuple[str, ...]


def entity_record(entity: Entity) -> dict[str, Any]:
    return {"kind": entity.kind, "position": entity.position, "cells": entity.cells, "color": entity.color, "state": dict(entity.state)}
