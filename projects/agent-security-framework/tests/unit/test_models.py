from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.models.canonical import canonical_json, stable_hash
from src.models.scenario import Scenario, ScenarioError, load_scenario

ROOT = Path(__file__).resolve().parents[2]


class ModelTests(unittest.TestCase):
    def test_valid_fixture(self) -> None:
        self.assertEqual(
            load_scenario(ROOT / "fixtures/synthetic_failure.json").schema_version, "1.0"
        )

    def test_invalid_scenario_rejected(self) -> None:
        with self.assertRaises(ScenarioError):
            Scenario.from_dict({"schema_version": "1.0"})

    def test_unknown_field_rejected(self) -> None:
        data = json.loads((ROOT / "fixtures/synthetic_failure.json").read_text())
        data["surprise"] = True
        with self.assertRaises(ScenarioError):
            Scenario.from_dict(data)

    def test_unknown_action_provenance_rejected(self) -> None:
        data = json.loads((ROOT / "fixtures/synthetic_failure.json").read_text())
        data["metadata"]["action_space"][0]["provenance"] = ["missing-artifact"]
        with self.assertRaisesRegex(ScenarioError, "unknown artifact"):
            Scenario.from_dict(data)

    def test_canonical_hash_order_independent(self) -> None:
        self.assertEqual(stable_hash({"a": 1, "b": 2}), stable_hash({"b": 2, "a": 1}))
        self.assertEqual(canonical_json({"b": 2, "a": 1}), '{"a":1,"b":2}')
