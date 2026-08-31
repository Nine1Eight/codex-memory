from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ghostbridge.causal_graph import CalibratedCausalGraph
from ghostbridge.counterfactual_engine import CounterfactualEngine
from ghostbridge.evidence_ledger import EvidenceLedger
from ghostbridge.hypothesis_engine import HypothesisEngine
from ghostbridge.integration import GhostBridgeV5Runtime
from ghostbridge.macro_compiler import MacroCompiler
from ghostbridge.macro_executor import MacroExecutor
from ghostbridge.memory_tiers import QuarantinedMemory
from ghostbridge.object_tracker import PersistentObjectTracker
from ghostbridge.region_model import RegionModel
from ghostbridge.schemas import ActionEvidence, ImmutableObservation
from ghostbridge.temporal_model import TemporalOwnership


def snap(frame, score=0.0, level=0, terminal=False):
    return {"grid": frame, "score": score, "levels": level, "game_over": terminal}


class GhostBridgeV5Acceptance(unittest.TestCase):
    def test_01_persistent_identity_through_movement_and_transformation(self):
        tracker = PersistentObjectTracker()
        first = ImmutableObservation.capture("g1", 0, ((0,2,2),(0,0,0)))
        second = ImmutableObservation.capture("g1", 1, ((0,0,0),(0,2,2)))
        left = tracker.update(first); right = tracker.update(second)
        self.assertEqual(left[0].object_id, right[0].object_id)

    def test_02_delayed_effect_waits_for_stability(self):
        temporal = TemporalOwnership(stable_frames=2, deadline_frames=5)
        pre = ImmutableObservation.capture("g", 0, ((0,1),))
        temporal.begin("g", 1, pre, "A1")
        moving = ImmutableObservation.capture("g", 1, ((1,0),))
        stable = ImmutableObservation.capture("g", 1, ((0,1),))
        self.assertFalse(temporal.observe("g", moving))
        self.assertFalse(temporal.observe("g", stable))
        self.assertTrue(temporal.observe("g", stable))
        post, window = temporal.settle("g")
        self.assertEqual(post.frame_hash, stable.frame_hash); self.assertEqual(len(window), 3)

    def test_03_prerequisite_discovery_uses_success_and_no_effect(self):
        runtime = GhostBridgeV5Runtime()
        runtime.prepare("g", {"id": 1}, snap(((0,1),)))
        no_effect = runtime.commit("g", snap(((0,1),)))
        runtime.prepare("g", {"id": 1}, snap(((0,1),)))
        success = runtime.commit("g", snap(((1,0),), score=1.0))
        kinds = {event.event_type for event in no_effect.events + success.events}
        self.assertIn("no_observed_effect", kinds); self.assertIn("reward", kinds)
        self.assertTrue(runtime.causal.beliefs)

    def test_04_competing_hypotheses_are_discriminated(self):
        engine = HypothesisEngine(); context = "c"
        left = engine.propose("A moves object", {"moved_or_transformed"}, context)
        right = engine.propose("A changes topology", {"reachability_candidate"}, context)
        pair = engine.competing_pair(context)
        self.assertIsNotNone(pair)
        self.assertEqual({item.hypothesis_id for item in pair}, {left.hypothesis_id, right.hypothesis_id})
        cf = CounterfactualEngine()
        self.assertEqual(cf.discriminating_action({1:{"move"},2:{"open"}}, {1:{"open"},2:{"open"}}), 1)

    def test_05_topology_and_reachability_change(self):
        model = RegionModel()
        before = ImmutableObservation.capture("g", 0, ((0,1,0),(0,1,0)))
        after = ImmutableObservation.capture("g", 1, ((0,0,0),(0,1,0)))
        self.assertGreater(model.topology(before)["region_count"], model.topology(after)["region_count"])

    def test_06_backward_credit_from_real_score(self):
        runtime = GhostBridgeV5Runtime()
        runtime.prepare("g", {"id": 1}, snap(((0,1),)))
        first = runtime.commit("g", snap(((1,0),)))
        runtime.prepare("g", {"id": 2}, snap(((1,0),)))
        reward = runtime.commit("g", snap(((1,0),), score=2.0))
        credited = {item["transition_id"] for item in reward.reward_attribution}
        self.assertIn(first.transition_id, credited); self.assertIn(reward.transition_id, credited)

    def test_07_macro_aborts_on_prediction_failure(self):
        macro = MacroCompiler().compile((1,2), (lambda state: state["ok"],), (lambda state: state["ok"], lambda state: state["ok"]), ("p1","p2"), 2)
        state = {"ok": True}; calls = []
        def execute(action): calls.append(action); state["ok"] = False
        result = MacroExecutor().execute(macro, state, execute, lambda: state)
        self.assertFalse(result.completed); self.assertEqual(result.actions_executed, 1)

    def test_08_memory_tiers_are_quarantined(self):
        memory = QuarantinedMemory(family_games=2, universal_games=3)
        one = memory.observe("g1", "c1", "door", "A1", True)
        self.assertFalse(memory.propose_family("family", [one])); self.assertFalse(memory.universal)
        two = memory.observe("g2", "c2", "door", "A1", True)
        self.assertTrue(memory.propose_family("family", [one,two])); self.assertFalse(memory.universal)

    def test_09_deterministic_ledger_replay(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"; runtime = GhostBridgeV5Runtime(path)
            runtime.prepare("g", {"id": 1}, snap(((0,1),)))
            runtime.commit("g", snap(((1,0),), score=1.0))
            replayed = EvidenceLedger.replay(path)
            self.assertEqual(runtime.ledger.replay_digest(), replayed.replay_digest())

    def test_10_identical_transition_boundary_and_zero_debt(self):
        runtime = GhostBridgeV5Runtime()
        pre = snap(((0,1),)); runtime.prepare("g", {"id": 1}, pre)
        envelope = runtime.commit("g", snap(((1,0),)))
        envelope.verify(); runtime.assert_zero_debt("g")
        with self.assertRaises(ValueError):
            replace(envelope, hashes={**envelope.hashes, "pre": "tampered"}).verify()


if __name__ == "__main__":
    unittest.main()
