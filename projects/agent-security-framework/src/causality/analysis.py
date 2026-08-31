"""Provenance graph and counterfactual replay."""

from __future__ import annotations

from dataclasses import dataclass

from src.models.scenario import Scenario
from src.oracles.failure import FailureOracle
from src.simulator.engine import Action, Simulator


@dataclass(frozen=True)
class CausalAnalysis:
    status: str
    nodes: tuple[dict[str, object], ...]
    edges: tuple[dict[str, object], ...]
    factual_failure: bool
    counterfactual_failure: bool


class CausalAnalyzer:
    def __init__(self, oracle: FailureOracle | None = None) -> None:
        self.oracle = oracle or FailureOracle()

    def analyze(self, scenario: Scenario, actions: list[Action]) -> CausalAnalysis:
        factual = Simulator(scenario).run(actions)
        factual_failure = bool(self.oracle.evaluate(scenario, factual))
        # Removing the suspected untrusted artifact also removes decisions whose
        # declared provenance depends on it; merely deleting a taint label would
        # hide influence while preserving its effect.
        neutral = [Action(a.tool, dict(a.parameters), ()) for a in actions if not a.provenance]
        counterfactual = Simulator(scenario).run(neutral)
        counterfactual_failure = bool(self.oracle.evaluate(scenario, counterfactual))
        status = (
            "confirmed"
            if factual_failure and not counterfactual_failure
            else "rejected"
            if not factual_failure
            else "uncertain"
        )
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        for event in factual.history:
            event_id = f"event:{event.index}"
            observation_id = f"observation:{event.index}"
            decision_id = f"decision:{event.index}"
            tool_id = f"tool_call:{event.index}"
            change_id = f"state_change:{event.index}"
            nodes.extend(
                (
                    {"id": observation_id, "type": "agent_observation", "trust": event.trust},
                    {"id": decision_id, "type": "agent_decision", "trust": event.trust},
                    {"id": tool_id, "type": "tool_call", "tool": event.tool},
                    {"id": event_id, "type": event.event_type, "trust": event.trust},
                    {"id": change_id, "type": "state_change", "state_hash": factual.state_hash},
                )
            )
            edges.extend(
                (
                    {"from": observation_id, "to": decision_id, "relation": "informs"},
                    {"from": decision_id, "to": tool_id, "relation": "requests"},
                    {"from": tool_id, "to": event_id, "relation": "produces"},
                    {"from": event_id, "to": change_id, "relation": "applies"},
                )
            )
            if event.event_type.startswith("permission_"):
                permission_id = f"permission:{event.index}"
                nodes.append(
                    {
                        "id": permission_id,
                        "type": "permission_transition",
                        "permission": event.permission,
                    }
                )
                edges.append(
                    {"from": event_id, "to": permission_id, "relation": "changes_authority"}
                )
            for source in event.provenance:
                nodes.append(
                    {"id": f"artifact:{source}", "type": "input_artifact", "trust": "untrusted"}
                )
                edges.append(
                    {"from": f"artifact:{source}", "to": observation_id, "relation": "observed"}
                )
            if event.index:
                edges.append(
                    {
                        "from": f"state_change:{event.index - 1}",
                        "to": observation_id,
                        "relation": "precedes",
                    }
                )
        if factual_failure and factual.history:
            outcome = "outcome:prohibited"
            nodes.append({"id": outcome, "type": "terminal_outcome", "status": status})
            edges.append(
                {"from": f"event:{factual.history[-1].index}", "to": outcome, "relation": "causes"}
            )
        unique_nodes = {str(n["id"]): n for n in nodes}
        return CausalAnalysis(
            status,
            tuple(unique_nodes.values()),
            tuple(edges),
            factual_failure,
            counterfactual_failure,
        )
