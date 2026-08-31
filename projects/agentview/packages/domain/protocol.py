from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import StrEnum
import base64
import hashlib
import json
from typing import Any, Protocol


class ViewClass(StrEnum):
    MULTIMODAL = "multimodal"
    TRANSCRIPT = "transcript"
    VISUAL = "visual"
    METADATA_OBSERVATION = "metadata_observation"


class AuthorityDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


def round2(value: float) -> float:
    return round(value + 1e-12, 2)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class Coverage:
    required: float
    audio: float = 0.0
    transcript: float = 0.0
    visual: float = 0.0

    def clamp(self) -> "Coverage":
        def c(v: float) -> float:
            return min(1.0, max(0.0, v))

        return Coverage(c(self.required), c(self.audio), c(self.transcript), c(self.visual))


@dataclass(frozen=True)
class EvidenceScore:
    evidence_alignment: float
    comprehension: float
    consistency: float
    outcome: float


@dataclass(frozen=True)
class ScoreBreakdown:
    coverage: Coverage
    evidence: EvidenceScore
    viewing_confidence: float


@dataclass(frozen=True)
class Claim:
    claim_id: str
    normalized_proposition: str
    importance: int
    stance: str
    evidence_refs: tuple[str, ...]
    support: float
    contradiction: float
    confidence: float


@dataclass(frozen=True)
class DeduplicationKeyInput:
    agent_id: str
    agent_version_id: str
    source_revision_fingerprint: str
    objective_canonical_sha256: str
    evidence_policy_version: str


@dataclass(frozen=True)
class ReceiptSignature:
    algorithm: str
    key_id: str
    value: str


@dataclass(frozen=True)
class ReceiptPayload:
    tenant_id: str
    agent_id: str
    agent_version_id: str
    key_id: str
    source_id: str
    source_revision_id: str
    source_type: str
    source_fingerprint_sha256: str
    external_reference: str | None
    duration_ms: int
    language_codes: tuple[str, ...]
    authority_class: str
    authority_decision: str
    policy_version: str
    objective_id: str
    objective_type: str
    canonical_sha256: str
    job_id: str
    delegation_mode: str
    started_at: str
    completed_at: str
    attempt_count: int
    view_class: ViewClass
    qualified: bool
    qualification_failures: tuple[str, ...]
    coverage: Coverage
    scores: ScoreBreakdown
    claims_count: int
    material_claim_count: int
    claims_merkle_root_sha256: str
    outcome_id: str
    outcome_schema_id: str
    outcome_content_sha256: str
    content_merit: None | dict[str, Any]
    deduplication_key_sha256: str
    created_at: str


@dataclass(frozen=True)
class AgentViewReceipt:
    schema_version: str
    receipt_id: str
    payload: ReceiptPayload
    signature: ReceiptSignature


class ReceiptVerifier(Protocol):
    def verify(self, receipt: AgentViewReceipt) -> bool: ...


def compute_deduplication_key(value: DeduplicationKeyInput) -> str:
    joined = "\x1f".join(
        [
            value.agent_id,
            value.agent_version_id,
            value.source_revision_fingerprint,
            value.objective_canonical_sha256,
            value.evidence_policy_version,
        ]
    )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def compute_claim_merkle_root(claims: list[Claim]) -> str:
    if not claims:
        raise ValueError("claim list cannot be empty")
    leaves = []
    for claim in sorted(claims, key=lambda item: item.claim_id):
        leaf = canonical_json(
            {
                "claim_id": claim.claim_id,
                "normalized_proposition": claim.normalized_proposition,
                "importance": claim.importance,
                "stance": claim.stance,
                "evidence_refs": list(claim.evidence_refs),
                "support": claim.support,
                "contradiction": claim.contradiction,
                "confidence": claim.confidence,
            }
        ).encode("utf-8")
        leaves.append(hashlib.sha256(leaf).digest())
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])
        leaves = [
            hashlib.sha256(leaves[i] + leaves[i + 1]).digest()
            for i in range(0, len(leaves), 2)
        ]
    return leaves[0].hex()


def _weighted_average(pairs: list[tuple[float, float]]) -> float:
    weight_sum = sum(weight for weight, _ in pairs)
    if weight_sum == 0:
        return 0.0
    return sum(weight * score for weight, score in pairs) / weight_sum


def compute_viewing_confidence(
    coverage: Coverage,
    evidence_alignment: float,
    comprehension: float,
    consistency: float,
    outcome: float,
) -> float:
    return round2(
        100
        * (
            0.30 * coverage.required
            + 0.30 * evidence_alignment
            + 0.25 * comprehension
            + 0.10 * consistency
            + 0.05 * outcome
        )
    )


def qualify_view(
    view_class: ViewClass,
    authority_decision: AuthorityDecision,
    coverage: Coverage,
    evidence_alignment: float,
    comprehension: float,
    consistency: float,
    outcome: float,
    critical_error: bool,
    qualification_failures: tuple[str, ...],
) -> tuple[bool, float]:
    vcs = compute_viewing_confidence(coverage, evidence_alignment, comprehension, consistency, outcome)
    qualified = (
        authority_decision == AuthorityDecision.ALLOW
        and view_class != ViewClass.METADATA_OBSERVATION
        and coverage.required >= 0.80
        and evidence_alignment >= 0.90
        and comprehension >= 0.75
        and consistency >= 0.90
        and outcome == 1
        and vcs >= 82.0
        and not critical_error
        and not qualification_failures
    )
    return qualified, vcs


class LocalSigner:
    def __init__(self, key_id: str, secret: bytes) -> None:
        self.key_id = key_id
        self.secret = secret

    def sign(self, payload: dict[str, Any]) -> ReceiptSignature:
        material = canonical_json(payload).encode("utf-8")
        digest = hashlib.sha256(self.secret + material).digest()
        return ReceiptSignature("Ed25519", self.key_id, base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii"))

    def verify(self, payload: dict[str, Any], signature: ReceiptSignature) -> bool:
        return self.sign(payload) == signature

