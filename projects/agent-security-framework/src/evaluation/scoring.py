"""Configurable trajectory evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from src.models.scenario import Scenario
from src.models.state import SimulatorState
from src.oracles.failure import Finding


@dataclass(frozen=True)
class EvaluationWeights:
    severity: float = 5.0
    state_coverage: float = 1.0
    tool_coverage: float = 1.0
    novelty: float = 2.0
    causality: float = 4.0
    replay: float = 4.0
    path_length: float = -0.1
    resource_cost: float = -0.05
    duplicate_similarity: float = -1.0
    schema_validity: float = 2.0


class Evaluator:
    def __init__(self, weights: EvaluationWeights | None = None) -> None:
        self.weights = weights or EvaluationWeights()

    def score(
        self,
        scenario: Scenario,
        state: SimulatorState,
        findings: tuple[Finding, ...],
        novel: bool,
        duplicate_similarity: float = 0.0,
    ) -> float:
        w = self.weights
        severity = max((finding.severity for finding in findings), default=0.0)
        causal = any(finding.untrusted_influence for finding in findings)
        reproducible = any(finding.reproducible for finding in findings)
        tool_coverage = len({event.tool for event in state.history})
        event_coverage = len({event.event_type for event in state.history})
        return (
            w.severity * severity
            + w.state_coverage * event_coverage
            + w.tool_coverage * tool_coverage
            + w.novelty * float(novel)
            + w.causality * float(causal)
            + w.replay * float(reproducible)
            + w.path_length * len(state.history)
            + w.resource_cost * len(state.history)
            + w.duplicate_similarity * duplicate_similarity
            + w.schema_validity
        )
