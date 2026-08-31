from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def evidence_id(kind: str, payload: Any, parents: tuple[str, ...] = ()) -> str:
    material = canonical({"kind": kind, "parents": parents, "payload": payload})
    return f"{kind[:3]}-{sha256(material.encode()).hexdigest()[:24]}"


class PlannerPhase(str, Enum):
    MAP_CONTROLS = "MAP_CONTROLS"
    DISCOVER_OBJECTS = "DISCOVER_OBJECTS"
    DISCOVER_MECHANICS = "DISCOVER_MECHANICS"
    FIRST_SCORE = "FIRST_SCORE"
    BACKTRACE_REWARD = "BACKTRACE_REWARD"
    VERIFY_REWARD_PATH = "VERIFY_REWARD_PATH"
    EXPAND_REWARD_PATH = "EXPAND_REWARD_PATH"
    EXPLOIT_PROVEN_MACROS = "EXPLOIT_PROVEN_MACROS"
    RECOVER = "RECOVER"


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    record_id: str
    kind: str
    payload: Mapping[str, Any]
    parents: tuple[str, ...] = ()
    game_id: str = ""
    transition_id: str = ""

    @classmethod
    def create(cls, kind: str, payload: Mapping[str, Any], parents=(), game_id="", transition_id=""):
        parents = tuple(parents)
        return cls(evidence_id(kind, payload, parents), kind, dict(payload), parents, game_id, transition_id)


@dataclass(frozen=True, slots=True)
class ImmutableObservation:
    observation_id: str
    game_id: str
    step: int
    frame_hash: str
    frame: tuple[tuple[int, ...], ...]
    score: float
    level: int
    terminal: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def capture(cls, game_id: str, step: int, frame, score=0.0, level=0, terminal=False, metadata=None):
        frozen = tuple(tuple(int(v) for v in row) for row in (frame or ()))
        payload = {"game_id": game_id, "step": step, "frame": frozen, "score": float(score), "level": int(level), "terminal": bool(terminal), "metadata": dict(metadata or {})}
        return cls(evidence_id("observation", payload), game_id, step, sha256(canonical(frozen).encode()).hexdigest(), frozen, float(score), int(level), bool(terminal), dict(metadata or {}))


@dataclass(frozen=True, slots=True)
class ActionEvidence:
    action_id: str
    game_id: str
    step: int
    action: str
    data: Mapping[str, Any]
    pre_observation_id: str

    @classmethod
    def capture(cls, game_id: str, step: int, action: Any, data: Mapping[str, Any], pre_observation_id: str):
        payload = {"game_id": game_id, "step": step, "action": str(action), "data": dict(data), "pre": pre_observation_id}
        return cls(evidence_id("action", payload, (pre_observation_id,)), game_id, step, str(action), dict(data), pre_observation_id)


@dataclass(frozen=True, slots=True)
class DeltaBundle:
    delta_id: str
    pre_observation_id: str
    post_observation_id: str
    changed_cells: tuple[tuple[int, int, int | None, int | None], ...]
    object_events: tuple[Mapping[str, Any], ...]
    topology_events: tuple[Mapping[str, Any], ...]
    score_delta: float
    level_delta: int
    dependency_group: str
    resolution: str


@dataclass(frozen=True, slots=True)
class TypedEvent:
    event_id: str
    event_type: str
    payload: Mapping[str, Any]
    parents: tuple[str, ...]
    confidence: float
    dependency_group: str


@dataclass(frozen=True, slots=True)
class PredictionAssessment:
    prediction_id: str
    error: float
    matched: tuple[str, ...]
    contradicted: tuple[str, ...]
    parents: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TransitionEnvelope:
    transition_id: str
    game_id: str
    step: int
    pre_observation: ImmutableObservation
    action: ActionEvidence
    post_observation: ImmutableObservation
    stabilization_observations: tuple[str, ...]
    delta: DeltaBundle
    events: tuple[TypedEvent, ...]
    prediction: Mapping[str, Any]
    assessment: PredictionAssessment
    hypothesis_updates: tuple[Mapping[str, Any], ...]
    reward_attribution: tuple[Mapping[str, Any], ...]
    planner_phase: PlannerPhase
    hashes: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["planner_phase"] = self.planner_phase.value
        return value

    def verify(self) -> None:
        if self.action.pre_observation_id != self.pre_observation.observation_id:
            raise ValueError("action/pre-observation provenance mismatch")
        if self.delta.pre_observation_id != self.pre_observation.observation_id or self.delta.post_observation_id != self.post_observation.observation_id:
            raise ValueError("delta observation provenance mismatch")
        expected = {
            "pre": self.pre_observation.observation_id,
            "action": self.action.action_id,
            "post": self.post_observation.observation_id,
            "delta": self.delta.delta_id,
            "events": sha256(canonical([e.event_id for e in self.events]).encode()).hexdigest(),
        }
        if dict(self.hashes) != expected:
            raise ValueError("transition evidence hashes disagree")
        material = {"game": self.game_id, "step": self.step, **expected}
        if self.transition_id != evidence_id("transition", material, tuple(expected.values())):
            raise ValueError("transition envelope identity mismatch")

