from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log
from typing import Any, Mapping

from .schemas import CanonicalRecord, EpistemicStatus, EvidenceVector, RecordType, Scope


@dataclass(slots=True)
class HypothesisBelief:
    hypothesis_id: str
    claim: str
    log_odds: float = 0.0
    evidence_groups: set[str] = field(default_factory=set)
    supporting: list[str] = field(default_factory=list)
    contradictory: list[str] = field(default_factory=list)

    @property
    def probability(self) -> float:
        return 1.0 / (1.0 + exp(-max(-30.0, min(30.0, self.log_odds))))


class HypothesisLedger:
    def __init__(self) -> None:
        self.beliefs: dict[str, HypothesisBelief] = {}

    def discover(self, hypothesis_id: str, claim: str, prior_probability: float = 0.5) -> HypothesisBelief:
        prior_probability = max(1e-6, min(1 - 1e-6, prior_probability))
        return self.beliefs.setdefault(hypothesis_id, HypothesisBelief(hypothesis_id, claim, log(prior_probability / (1-prior_probability))))

    def update_group(self, hypothesis_id: str, evidence_records: tuple[CanonicalRecord, ...]) -> dict[str, Any]:
        belief = self.beliefs[hypothesis_id]
        if not evidence_records: return {"hypothesis_id": hypothesis_id, "probability": belief.probability, "applied": False}
        groups = {record.independence_group for record in evidence_records}
        if len(groups) != 1: raise ValueError("evidence must be aggregated by one independence group")
        group = next(iter(groups))
        if group in belief.evidence_groups: return {"hypothesis_id": hypothesis_id, "probability": belief.probability, "applied": False}
        # One likelihood update per causal episode. Multiple detector views improve rho,
        # not the number of Bayesian updates.
        weighted_lr = 0.0; total_weight = 0.0
        for record in evidence_records:
            payload = record.payload; vector = EvidenceVector(**payload["evidence_vector"])
            detector_rho = sum(max(0.0, min(1.0, value)) for value in vector.values()) / 6.0
            rho = detector_rho * float(payload.get("dependence_discount", 1.0)) * float(payload.get("temporal_discount", 1.0)) * float(payload.get("context_discount", 1.0))
            rho = max(0.0, min(1.0, rho))
            likelihood_h = max(1e-6, min(1-1e-6, float(payload["likelihood_given_h"])))
            likelihood_not_h = max(1e-6, min(1-1e-6, float(payload["likelihood_given_not_h"])))
            weighted_lr += rho * log(likelihood_h / likelihood_not_h); total_weight += rho
        belief.log_odds += weighted_lr / max(1.0, total_weight)
        belief.evidence_groups.add(group)
        ids = [record.record_id for record in evidence_records]
        if weighted_lr >= 0: belief.supporting.extend(ids)
        else: belief.contradictory.extend(ids)
        return {"hypothesis_id": hypothesis_id, "probability": belief.probability, "log_odds": belief.log_odds, "applied": True, "independence_group": group, "evidence_ids": tuple(ids), "polarity": "support" if weighted_lr >= 0 else "negative"}

