from __future__ import annotations
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from adapters.base import Observation
from adl import DifferenceEngine, ReflectionEngine
from detectors import PerceptionEngine
from ghostbridge import GhostBridge
from planning.planner import ActionValidationError, ActionValidator
from prl.sid import SemanticIDDecoder
from world.causal import CausalTransitionGraph
from world.state import Action
from world.twin import EnvironmentTwin

class VerticalSlices(unittest.TestCase):
    def setUp(self):
        self.perception=PerceptionEngine(); self.detectors=("grid","components","objects","topology","frame_difference","novelty")
        self.first=Observation(((0,0,0),(0,2,0),(0,0,3)),(Action(1),Action(2)),"xy01-v2")
        self.second=Observation(((0,0,0),(0,0,2),(0,0,3)),(Action(1),Action(2)),"xy01-v2",progress=0.0)

    def test_slice1_observation_state_delta(self):
        a=self.perception.process(self.first,self.detectors); b=self.perception.process(self.second,self.detectors,a); delta=DifferenceEngine().diff(a,b)
        self.assertTrue(delta.changed); self.assertTrue(any(c.kind.value=="MOVED" for c in delta.entity_changes)); ActionValidator().validate(Action(1),a)
        with self.assertRaises(ActionValidationError): ActionValidator().validate(Action(7),a)

    def test_slice2_prediction_reflection_learning(self):
        a=self.perception.process(self.first,self.detectors); twin=EnvironmentTwin(); prediction=twin.predict(a,Action(1)); b=self.perception.process(self.second,self.detectors,a)
        delta=DifferenceEngine().diff(a,b); reflection=ReflectionEngine().reflect(prediction,b,delta); graph=CausalTransitionGraph(); graph.update(a,Action(1),b,reflection); twin.update(a,reflection)
        self.assertEqual(len(graph.transitions),1); self.assertEqual(twin.global_effects[1].trials,1)

    def test_slice3_ghostbridge_falsifiable(self):
        world=self.perception.process(self.first,self.detectors); ghost=GhostBridge(); gap=ghost.find_gap(world,CausalTransitionGraph()); self.assertIsNotNone(gap)
        hypothesis=ghost.best_hypothesis(gap,world); self.assertTrue(hypothesis.claim); self.assertTrue(hypothesis.minimum_discriminating_test)

    def test_sid_observation_authority(self):
        sid=SemanticIDDecoder({"prefix:xy":{"detector:grid":0.1}}); world=self.perception.process(self.first,self.detectors); prior=sid.infer("xy01-v2",world.fingerprint)
        sid.update(prior,world.fingerprint,{"detector:grid":1.0}); self.assertGreater(sid.infer("xy01-v2",world.fingerprint).detectors["grid"],.5)

if __name__=="__main__": unittest.main()
