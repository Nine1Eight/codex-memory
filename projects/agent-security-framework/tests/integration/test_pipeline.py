from __future__ import annotations

import unittest
from pathlib import Path

from src.causality.analysis import CausalAnalyzer
from src.models.canonical import canonical_json
from src.models.scenario import Scenario, load_scenario
from src.oracles.failure import FailureOracle
from src.replay.manager import ReplayManager
from src.search.engine import STRATEGIES, SearchEngine
from src.simulator.engine import Action, Simulator

ROOT = Path(__file__).resolve().parents[2]


class PipelineTests(unittest.TestCase):
    scenario: Scenario
    actions: list[Action]

    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_scenario(ROOT / "fixtures/synthetic_failure.json")
        cls.actions = Simulator.actions_from_json(
            (ROOT / "fixtures/failure_actions.json").read_text()
        )

    def test_failure_detected(self) -> None:
        findings = FailureOracle().evaluate(
            self.scenario, Simulator(self.scenario).run(self.actions)
        )
        self.assertEqual([finding.rule_id for finding in findings], ["SIMULATED_EXTERNAL_SEND"])
        self.assertTrue(findings[0].authority_exceeded)

    def test_all_search_strategies_find_fixture(self) -> None:
        for strategy in sorted(STRATEGIES):
            with self.subTest(strategy=strategy):
                engine = SearchEngine(self.scenario, strategy)
                results = engine.explore()
                self.assertTrue(results)
                self.assertTrue(
                    all(
                        f.reproducible and f.causal_status == "confirmed"
                        for r in results
                        for f in r.findings
                    )
                )
                self.assertIn("SIMULATED_EXTERNAL_SEND", engine.archive.terminal_outcomes)

    def test_causality_counterfactual(self) -> None:
        result = CausalAnalyzer().analyze(self.scenario, self.actions)
        self.assertEqual(result.status, "confirmed")
        self.assertTrue(result.factual_failure)
        self.assertFalse(result.counterfactual_failure)
        node_types = {str(node["type"]) for node in result.nodes}
        self.assertTrue(
            {
                "input_artifact",
                "agent_observation",
                "agent_decision",
                "tool_call",
                "state_change",
                "permission_transition",
                "terminal_outcome",
            }.issubset(node_types)
        )

    def test_minimization_preserves_outcome(self) -> None:
        manager = ReplayManager()
        minimized = manager.minimize(self.scenario, self.actions)
        self.assertLessEqual(len(minimized), len(self.actions))
        self.assertTrue(
            FailureOracle().evaluate(self.scenario, Simulator(self.scenario).run(minimized))
        )

    def test_stateful_search_strategies_are_deterministic(self) -> None:
        for strategy in ("mcts", "bandit", "evolutionary"):
            with self.subTest(strategy=strategy):
                left = SearchEngine(self.scenario, strategy).explore()
                right = SearchEngine(self.scenario, strategy).explore()
                self.assertEqual(canonical_json(left), canonical_json(right))
