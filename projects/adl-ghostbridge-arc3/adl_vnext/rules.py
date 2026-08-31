from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import RuleState


@dataclass(slots=True)
class RuleVersion:
    rule_id: str
    version: int
    statement: str
    state: RuleState
    predecessor_id: str | None = None
    support: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    conditions: tuple[str, ...] = ()


class RuleLedger:
    ALLOWED = {
        RuleState.DISCOVERED: {RuleState.TENTATIVE, RuleState.DISPROVEN},
        RuleState.TENTATIVE: {RuleState.SUPPORTED, RuleState.CONTRADICTED, RuleState.DISPROVEN},
        RuleState.SUPPORTED: {RuleState.CONFIRMED, RuleState.CONTRADICTED, RuleState.DISPROVEN},
        RuleState.CONFIRMED: {RuleState.GENERALIZED, RuleState.CONTRADICTED, RuleState.DISPROVEN},
        RuleState.GENERALIZED: {RuleState.CONTRADICTED, RuleState.DISPROVEN},
        RuleState.CONTRADICTED: {RuleState.REFINED, RuleState.INVALIDATED},
        RuleState.REFINED: {RuleState.SUPPORTED, RuleState.CONTRADICTED, RuleState.DISPROVEN},
        RuleState.DISPROVEN: {RuleState.INVALIDATED}, RuleState.INVALIDATED: {RuleState.ARCHIVED}, RuleState.ARCHIVED: set(),
    }

    def __init__(self, policy: dict[str, float] | None = None) -> None:
        self.policy = policy or {"support_threshold": 3, "contradiction_rate": 0.25, "half_life": 120, "prune_age": 500, "confidence_floor": 0.05}
        self.versions: dict[str, list[RuleVersion]] = {}

    def discover(self, rule_id: str, statement: str, evidence_id: str) -> RuleVersion:
        rule = RuleVersion(rule_id, 1, statement, RuleState.DISCOVERED, support=[evidence_id]); self.versions.setdefault(rule_id, []).append(rule); return rule

    def transition(self, rule_id: str, target: RuleState, evidence_id: str, *, refined_statement: str | None = None, conditions=()) -> RuleVersion:
        current = self.versions[rule_id][-1]
        if target not in self.ALLOWED[current.state]: raise ValueError(f"illegal rule transition {current.state.value}->{target.value}")
        if target == RuleState.REFINED:
            if not refined_statement: raise ValueError("refinement requires a new statement")
            updated = RuleVersion(rule_id, current.version + 1, refined_statement, target, f"{rule_id}:v{current.version}", list(current.support), list(current.contradictions), tuple(conditions))
        else:
            updated = RuleVersion(rule_id, current.version, current.statement, target, current.predecessor_id, list(current.support), list(current.contradictions), current.conditions)
        (updated.contradictions if target in {RuleState.CONTRADICTED,RuleState.DISPROVEN,RuleState.INVALIDATED} else updated.support).append(evidence_id)
        self.versions[rule_id].append(updated); return updated

