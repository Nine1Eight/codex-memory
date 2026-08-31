from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adl_vnext.authority import ADLAuthority
from adl_vnext.coordinator import ADLVNextCoordinator
from adl_vnext.ghostbridge_model import GhostBridgeWorldModel
from adl_vnext.hypotheses import HypothesisLedger
from adl_vnext.ownership import assert_owner
from adl_vnext.replay import KnowledgeReplay
from adl_vnext.rdl_boundary import RDLBoundary
from adl_vnext.rhae_gateway import RHAECommitGateway
from adl_vnext.schemas import CanonicalRecord, EpistemicStatus, EvidenceVector, ExperimentProposal, GhostBridgeForecast, KnowledgeSnapshot, RecordType, Scope
from adl_vnext.transaction_log import TransactionLog


class ADLVNextContractTests(unittest.TestCase):
    def test_ownership_boundary_blocks_wrong_owner(self):
        assert_owner("ADL","evidence")
        with self.assertRaises(PermissionError): assert_owner("GhostBridge","rule_promotion")
        with self.assertRaises(PermissionError): assert_owner("ADL","action_commit")

    def test_negative_evidence_reduces_belief_and_group_counts_once(self):
        ledger=HypothesisLedger(); belief=ledger.discover("h","action opens door",0.5); scope=Scope("g","e",1,"t","c")
        payload={"evidence_vector":{"detection":1,"reliability":1,"semantic":1,"temporal":1,"independence":1,"novelty":1},"likelihood_given_h":0.2,"likelihood_given_not_h":0.8,"dependence_discount":1,"temporal_discount":1,"context_discount":1}
        one=CanonicalRecord.create(RecordType.EVIDENCE_EVENT,scope,payload,independence_group="group")
        two=CanonicalRecord.create(RecordType.EVIDENCE_EVENT,scope,{**payload,"detector":"object"},independence_group="group")
        result=ledger.update_group("h",(one,two)); after=belief.probability
        self.assertLess(after,0.5); self.assertTrue(result["applied"])
        self.assertFalse(ledger.update_group("h",(one,two))["applied"]); self.assertEqual(after,belief.probability)

    def test_transaction_log_is_hash_chained_and_replayable(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/"ledger.jsonl"; log=TransactionLog(path); scope=Scope("g","e",1,"t","c")
            record=CanonicalRecord.create(RecordType.OBSERVATION_SNAPSHOT,scope,{"frame":((0,),)})
            tx=log.commit((record,)); replay=TransactionLog.replay(path)
            self.assertEqual(tx.digest,replay.head_digest); self.assertEqual(1,len(replay.transactions))

    def test_rhae_commits_exactly_one_legal_action(self):
        gateway=RHAECommitGateway(); scope=Scope("g","e",1,"t","c")
        proposal=ExperimentProposal("p","A1",{},(),0.5,{}, {},1.0,())
        forecast=GhostBridgeForecast("p",(),0.1,0.0,0.0,0.0,1.0,"pred","snap")
        _,_,chosen,_,_=gateway.choose(scope,(proposal,),(forecast,))
        record=gateway.commit_external(scope,chosen.action,{},("A1",))
        self.assertEqual(record.record_type,RecordType.ACTION_COMMIT); self.assertTrue(record.payload["exactly_one"])
        with self.assertRaises(ValueError): gateway.commit_external(scope,"A2",{},("A1",))

    def test_ghostbridge_consumes_only_sealed_snapshot_and_cannot_promote(self):
        bridge=GhostBridgeWorldModel(); snapshot=KnowledgeSnapshot.seal("g","e",0,(),(),(),{}, {},(),{},"ctx")
        bridge.publish(snapshot,{})
        self.assertFalse(hasattr(bridge,"promote_rule")); self.assertFalse(hasattr(bridge,"update_hypothesis"))

    def test_full_cycle_zero_debt_and_identical_replay_digest(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/"adl.jsonl"; coordinator=ADLVNextCoordinator(path)
            pre={"grid":((0,1),(0,0)),"score":0,"levels":0}; post={"grid":((1,0),(0,0)),"score":1,"levels":1}
            snapshot=coordinator.record_external_action("g",{"id":"A1"},pre,post,legal_actions=("A1",))
            self.assertEqual(0,coordinator.rdl.debt("g"))
            replay=KnowledgeReplay().from_path(path)["g"]
            self.assertEqual(snapshot.knowledge_digest,replay.knowledge_digest)

    def test_observed_inferred_hypothesized_statuses_are_distinct(self):
        scope=Scope("g","e",1,"t","c")
        observed=CanonicalRecord.create(RecordType.OBSERVATION_SNAPSHOT,scope,{},status=EpistemicStatus.OBSERVED)
        inferred=CanonicalRecord.create(RecordType.CONCLUSION_BUNDLE,scope,{},status=EpistemicStatus.INFERRED)
        hypothesized=CanonicalRecord.create(RecordType.HYPOTHESIS_RECORD,scope,{},status=EpistemicStatus.HYPOTHESIZED)
        self.assertEqual(3,len({observed.epistemic_status,inferred.epistemic_status,hypothesized.epistemic_status}))


if __name__=="__main__": unittest.main()
