from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping


SCHEMA_VERSION = "adl.vnext.1"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return sha256(canonical(value).encode()).hexdigest()


class EpistemicStatus(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    HYPOTHESIZED = "HYPOTHESIZED"
    CONTRADICTED = "CONTRADICTED"
    DISPROVEN = "DISPROVEN"


class RecordType(str, Enum):
    OBSERVATION_SNAPSHOT = "ObservationSnapshot"
    ACTION_COMMIT = "ActionCommit"
    DIFFERENCE_PACKET = "DifferencePacket"
    TEMPORAL_EFFECT = "TemporalEffect"
    EVIDENCE_EVENT = "EvidenceEvent"
    HYPOTHESIS_RECORD = "HypothesisRecord"
    CONTRADICTION_RECORD = "ContradictionRecord"
    RULE_RECORD = "RuleRecord"
    OBJECT_MODEL = "ObjectModel"
    REGION_MODEL = "RegionModel"
    CAUSAL_RELATION = "CausalRelation"
    EXPERIMENT_PROPOSAL = "ExperimentProposal"
    CONCLUSION_BUNDLE = "ConclusionBundle"
    KNOWLEDGE_SNAPSHOT = "KnowledgeSnapshot"


class CausalLevel(str, Enum):
    OBSERVED_ASSOCIATION = "OBSERVED_ASSOCIATION"
    REPEATED_ASSOCIATION = "REPEATED_ASSOCIATION"
    INTERVENTION_SUPPORTED = "INTERVENTION_SUPPORTED"
    COUNTERFACTUALLY_DISTINGUISHED = "COUNTERFACTUALLY_DISTINGUISHED"
    CONTEXT_GENERALIZED = "CONTEXT_GENERALIZED"
    CAUSALLY_CONFIRMED = "CAUSALLY_CONFIRMED"


class RuleState(str, Enum):
    DISCOVERED = "DISCOVERED"
    TENTATIVE = "TENTATIVE"
    SUPPORTED = "SUPPORTED"
    CONFIRMED = "CONFIRMED"
    GENERALIZED = "GENERALIZED"
    CONTRADICTED = "CONTRADICTED"
    REFINED = "REFINED"
    DISPROVEN = "DISPROVEN"
    INVALIDATED = "INVALIDATED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True, slots=True)
class Scope:
    game_id: str
    episode_id: str
    cycle: int
    transition_id: str
    context_signature: str


@dataclass(frozen=True, slots=True)
class CanonicalRecord:
    record_id: str
    record_type: RecordType
    schema_version: str
    scope: Scope
    provenance: tuple[str, ...]
    epistemic_status: EpistemicStatus
    logical_timestamp: int
    supersedes: tuple[str, ...]
    superseded_at: int | None
    independence_group: str
    payload: Mapping[str, Any]
    canonical_digest: str

    @classmethod
    def create(cls, record_type: RecordType, scope: Scope, payload: Mapping[str, Any], *, provenance=(), status=EpistemicStatus.OBSERVED, timestamp: int | None = None, supersedes=(), superseded_at=None, independence_group=""):
        timestamp = scope.cycle if timestamp is None else int(timestamp)
        body = {"record_type": record_type.value, "schema_version": SCHEMA_VERSION, "scope": asdict(scope), "provenance": tuple(provenance), "epistemic_status": status.value, "logical_timestamp": timestamp, "supersedes": tuple(supersedes), "superseded_at": superseded_at, "independence_group": independence_group, "payload": dict(payload)}
        value_digest = digest(body)
        return cls(f"{record_type.value[:3].lower()}-{value_digest[:24]}", record_type, SCHEMA_VERSION, scope, tuple(provenance), status, timestamp, tuple(supersedes), superseded_at, independence_group, dict(payload), value_digest)

    def verify(self) -> None:
        rebuilt = CanonicalRecord.create(self.record_type, self.scope, self.payload, provenance=self.provenance, status=self.epistemic_status, timestamp=self.logical_timestamp, supersedes=self.supersedes, superseded_at=self.superseded_at, independence_group=self.independence_group)
        if rebuilt.record_id != self.record_id or rebuilt.canonical_digest != self.canonical_digest:
            raise ValueError(f"record digest mismatch: {self.record_id}")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self); value["record_type"] = self.record_type.value; value["epistemic_status"] = self.epistemic_status.value
        return value


@dataclass(frozen=True, slots=True)
class EvidenceVector:
    detection: float
    reliability: float
    semantic: float
    temporal: float
    independence: float
    novelty: float

    def values(self) -> tuple[float, ...]:
        return (self.detection, self.reliability, self.semantic, self.temporal, self.independence, self.novelty)


@dataclass(frozen=True, slots=True)
class ExperimentProposal:
    proposal_id: str
    action: str
    action_data: Mapping[str, Any]
    hypothesis_ids: tuple[str, ...]
    epistemic_value: float
    expected_result: Mapping[str, Any]
    falsification_result: Mapping[str, Any]
    reversibility: float
    provenance: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GhostBridgeForecast:
    proposal_id: str
    predicted_events: tuple[str, ...]
    progress_probability: float
    reward_probability: float
    reachability_delta: float
    failure_probability: float
    reversibility: float
    prediction_id: str
    snapshot_digest: str
    causal_level: CausalLevel = CausalLevel.OBSERVED_ASSOCIATION


@dataclass(frozen=True, slots=True)
class ValueVector:
    C: float; R: float; G: float; H: float; T: float; U: float
    KG: float; E: float; X: float; F: float; P: float


@dataclass(frozen=True, slots=True)
class ValueProducts:
    epistemic_value: float
    strategic_value: float
    decision_utility: float
    vector: ValueVector
    mode: str


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    snapshot_id: str
    schema_version: str
    game_id: str
    episode_id: str
    cycle: int
    record_ids: tuple[str, ...]
    observations: tuple[str, ...]
    evidence: tuple[str, ...]
    hypotheses: Mapping[str, float]
    rules: Mapping[str, str]
    conclusions: tuple[str, ...]
    uncertainty: Mapping[str, float]
    context_signature: str
    knowledge_digest: str

    @classmethod
    def seal(cls, game_id: str, episode_id: str, cycle: int, record_ids, observations, evidence, hypotheses, rules, conclusions, uncertainty, context_signature):
        body = {"schema_version": SCHEMA_VERSION, "game_id": game_id, "episode_id": episode_id, "cycle": cycle, "record_ids": tuple(record_ids), "observations": tuple(observations), "evidence": tuple(evidence), "hypotheses": dict(sorted(hypotheses.items())), "rules": dict(sorted(rules.items())), "conclusions": tuple(conclusions), "uncertainty": dict(sorted(uncertainty.items())), "context_signature": context_signature}
        kd = digest(body)
        return cls(f"kno-{kd[:24]}", SCHEMA_VERSION, game_id, episode_id, cycle, tuple(record_ids), tuple(observations), tuple(evidence), body["hypotheses"], body["rules"], tuple(conclusions), body["uncertainty"], context_signature, kd)


def record_from_dict(raw: Mapping[str, Any]) -> CanonicalRecord:
    value = dict(raw); value["record_type"] = RecordType(value["record_type"]); value["epistemic_status"] = EpistemicStatus(value["epistemic_status"]); value["scope"] = Scope(**value["scope"]); value["provenance"] = tuple(value["provenance"]); value["supersedes"] = tuple(value["supersedes"])
    return CanonicalRecord(**value)
