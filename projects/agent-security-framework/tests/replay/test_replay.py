from __future__ import annotations

import unittest
from pathlib import Path

from src.models.scenario import load_scenario
from src.replay.manager import ReplayManager
from src.simulator.engine import Simulator

ROOT = Path(__file__).resolve().parents[2]


class ReplayTests(unittest.TestCase):
    def test_three_clean_replays_match(self) -> None:
        scenario = load_scenario(ROOT / "fixtures/synthetic_failure.json")
        actions = Simulator.actions_from_json((ROOT / "fixtures/failure_actions.json").read_text())
        manager = ReplayManager()
        result = manager.verify(scenario, manager.package(scenario, actions), runs=3)
        self.assertTrue(result.reliable)
        self.assertTrue(result.findings)
        self.assertTrue(all(finding.reproducible for finding in result.findings))

    def test_minimized_artifact_contains_replay_and_causality(self) -> None:
        scenario = load_scenario(ROOT / "fixtures/synthetic_failure.json")
        actions = Simulator.actions_from_json((ROOT / "fixtures/failure_actions.json").read_text())
        artifact = ReplayManager().minimize_to_artifact(scenario, actions, runs=3)
        exported = artifact.export()
        self.assertTrue(artifact.replay.reliable)
        self.assertEqual(artifact.causality.status, "confirmed")
        self.assertIn("replay_package", exported)
        self.assertIn("explanation", exported)
