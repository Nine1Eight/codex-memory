from __future__ import annotations

import unittest
from pathlib import Path

from src.models.scenario import load_scenario
from src.oracles.failure import FailureOracle
from src.simulator.engine import Action, Simulator, TransitionError

ROOT = Path(__file__).resolve().parents[2]


class SimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = load_scenario(ROOT / "fixtures/synthetic_failure.json")

    def test_identical_runs_have_identical_events_and_hashes(self) -> None:
        actions = Simulator.actions_from_json((ROOT / "fixtures/failure_actions.json").read_text())
        first, second = Simulator(self.scenario).run(actions), Simulator(self.scenario).run(actions)
        self.assertEqual(first.history, second.history)
        self.assertEqual(first.state_hash, second.state_hash)

    def test_snapshot_round_trip(self) -> None:
        actions = Simulator.actions_from_json((ROOT / "fixtures/failure_actions.json").read_text())
        state = Simulator(self.scenario).run(actions)
        restored = Simulator.restore_snapshot(Simulator.snapshot(state))
        self.assertEqual(restored, state)
        self.assertEqual(restored.state_hash, state.state_hash)

    def test_unavailable_tool_fails_closed(self) -> None:
        with self.assertRaises(TransitionError):
            Simulator(self.scenario).run([Action("real_browser", {}, ())])

    def test_parameter_types_fail_closed(self) -> None:
        with self.assertRaisesRegex(TransitionError, "must be string"):
            Simulator(self.scenario).run(
                [Action("files", {"operation": 1, "path": "/reports/demo.txt", "content": ""}, ())]
            )

    def test_shell_text_is_only_recorded_data(self) -> None:
        marker = "/tmp/AGENTSEC_MUST_NOT_EXIST"
        actions = [
            Action(
                "authority",
                {"operation": "grant", "permission": "send_external"},
                ("untrusted-note",),
            ),
            Action(
                "mail",
                {
                    "recipient": "external@example.test",
                    "subject": "synthetic",
                    "body": f"touch {marker}",
                },
                ("untrusted-note",),
            ),
        ]
        state = Simulator(self.scenario).run(actions)
        self.assertEqual(state.messages[-1]["body"], f"touch {marker}")
        self.assertFalse(Path(marker).exists())

    def test_control_is_not_failure(self) -> None:
        actions = Simulator.actions_from_json((ROOT / "fixtures/control_actions.json").read_text())
        self.assertEqual(
            FailureOracle().evaluate(self.scenario, Simulator(self.scenario).run(actions)), []
        )
