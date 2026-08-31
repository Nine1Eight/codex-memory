from __future__ import annotations

import unittest
from pathlib import Path

from src.models.scenario import load_scenario
from src.oracles.failure import FailureOracle
from src.simulator.defense import SemanticDefense
from src.simulator.engine import Simulator

ROOT = Path(__file__).resolve().parents[2]


class AttackDefenseTests(unittest.TestCase):
    def test_same_attack_succeeds_unprotected_and_is_blocked_when_defended(self) -> None:
        scenario = load_scenario(ROOT / "fixtures/synthetic_failure.json")
        actions = Simulator.actions_from_json((ROOT / "fixtures/failure_actions.json").read_text())
        unprotected = Simulator(scenario).run(actions)
        defended = Simulator(scenario, defense=SemanticDefense()).run(actions)
        self.assertTrue(FailureOracle().evaluate(scenario, unprotected))
        self.assertFalse(FailureOracle().evaluate(scenario, defended))
        self.assertEqual(
            [event.event_type for event in defended.history], ["defense_blocked", "defense_blocked"]
        )
        self.assertEqual(defended.permissions, frozenset({"file_access", "manage_permissions"}))

    def test_low_risk_legitimate_action_remains_available(self) -> None:
        scenario = load_scenario(ROOT / "fixtures/synthetic_failure.json")
        actions = Simulator.actions_from_json((ROOT / "fixtures/control_actions.json").read_text())
        defended = Simulator(scenario, defense=SemanticDefense()).run(actions)
        self.assertEqual(defended.history[0].event_type, "virtual_file_read")
