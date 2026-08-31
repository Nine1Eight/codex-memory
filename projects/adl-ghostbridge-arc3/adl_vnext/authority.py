from __future__ import annotations

import copy
from hashlib import sha256
from typing import Any, Mapping

from .conclusions import ADLConclusionCompiler
from .hypotheses import HypothesisLedger
from .rules import RuleLedger
from .schemas import CanonicalRecord, EpistemicStatus, EvidenceVector, ExperimentProposal, KnowledgeSnapshot, RecordType, RuleState, Scope, canonical, digest
from .transaction_log import TransactionLog


class ADLAuthority:
    """Epistemic authority. Produces records and proposals; never commits actions."""

    def __init__(self, log: TransactionLog) -> None:
        self.log = log; self.hypotheses = HypothesisLedger(); self.rules = RuleLedger(); self.conclusions = ADLConclusionCompiler()
        self.records: dict[str, CanonicalRecord] = {}; self.snapshots: dict[str, KnowledgeSnapshot] = {}; self.uncertainty: dict[str, dict[str,float]] = {}

    def register_hypothesis(self, hypothesis_id: str, claim: str, prior=0.5) -> None:
        self.hypotheses.discover(hypothesis_id, claim, prior)

    def propose_experiments(self, snapshot: KnowledgeSnapshot, legal_actions: tuple[tuple[str, Mapping[str,Any]], ...]) -> tuple[ExperimentProposal, ...]:
        proposals = []
        hypotheses = tuple(sorted(snapshot.hypotheses, key=lambda key: abs(snapshot.hypotheses[key]-0.5)))
        uncertainty = sum(snapshot.uncertainty.values()) / max(1, len(snapshot.uncertainty))
        for action, data in legal_actions:
            body = {"snapshot": snapshot.knowledge_digest, "action": action, "data": dict(data), "hypotheses": hypotheses[:3]}
            pid = "exp-" + digest(body)[:24]
            proposals.append(ExperimentProposal(pid, action, dict(data), hypotheses[:3], min(1.0, 0.25+uncertainty), {"observable_change": True}, {"no_change_or_competing_effect": True}, 1.0, (snapshot.snapshot_id,)))
        return tuple(proposals)

    def ingest(self, scope: Scope, *, pre: Mapping[str,Any], action_commit: CanonicalRecord, post: Mapping[str,Any], difference: Mapping[str,Any], temporal: Mapping[str,Any], evidence_inputs: tuple[Mapping[str,Any], ...], conclusion_input: Mapping[str,Any] | None = None) -> KnowledgeSnapshot:
        independence_group = f"episode:{scope.episode_id}:transition:{scope.transition_id}"
        pre_record = CanonicalRecord.create(RecordType.OBSERVATION_SNAPSHOT, scope, pre, status=EpistemicStatus.OBSERVED, independence_group=independence_group)
        post_record = CanonicalRecord.create(RecordType.OBSERVATION_SNAPSHOT, scope, post, provenance=(pre_record.record_id, action_commit.record_id), status=EpistemicStatus.OBSERVED, independence_group=independence_group)
        temporal_record = CanonicalRecord.create(RecordType.TEMPORAL_EFFECT, scope, temporal, provenance=(action_commit.record_id, post_record.record_id), status=EpistemicStatus.OBSERVED, independence_group=independence_group)
        difference_record = CanonicalRecord.create(RecordType.DIFFERENCE_PACKET, scope, difference, provenance=(pre_record.record_id, post_record.record_id, temporal_record.record_id), status=EpistemicStatus.OBSERVED, independence_group=independence_group)
        evidence = []
        for item in evidence_inputs:
            payload = dict(item); payload.setdefault("independence_group", independence_group)
            evidence.append(CanonicalRecord.create(RecordType.EVIDENCE_EVENT, scope, payload, provenance=(difference_record.record_id, temporal_record.record_id), status=EpistemicStatus.OBSERVED, independence_group=independence_group))

        staged_hypotheses = copy.deepcopy(self.hypotheses); staged_rules = copy.deepcopy(self.rules); derived = []
        hypothesis_id = "hyp-" + digest({"action": action_commit.payload["action"], "context": scope.context_signature})[:20]
        staged_hypotheses.discover(hypothesis_id, f"{action_commit.payload['action']} produces progress or reward in {scope.context_signature}", 0.5)
        for hypothesis_id in sorted(staged_hypotheses.beliefs):
            update = staged_hypotheses.update_group(hypothesis_id, tuple(evidence))
            if not update.get("applied"): continue
            status = EpistemicStatus.INFERRED if update["polarity"] == "support" else EpistemicStatus.CONTRADICTED
            record_type = RecordType.HYPOTHESIS_RECORD if status == EpistemicStatus.INFERRED else RecordType.CONTRADICTION_RECORD
            derived.append(CanonicalRecord.create(record_type, scope, update, provenance=tuple(update["evidence_ids"]), status=status, independence_group=independence_group))

        belief = staged_hypotheses.beliefs[hypothesis_id]
        rule_id = "rule-" + digest({"hypothesis": hypothesis_id})[:20]
        evidence_id = evidence[0].record_id
        rule = None
        if rule_id not in staged_rules.versions and belief.supporting:
            rule = staged_rules.discover(rule_id, belief.claim, evidence_id)
        elif rule_id in staged_rules.versions:
            current = staged_rules.versions[rule_id][-1]
            if belief.contradictory and current.state in {RuleState.TENTATIVE,RuleState.SUPPORTED,RuleState.CONFIRMED,RuleState.GENERALIZED}:
                rule = staged_rules.transition(rule_id,RuleState.CONTRADICTED,evidence_id)
            elif belief.supporting:
                next_state = {RuleState.DISCOVERED:RuleState.TENTATIVE,RuleState.TENTATIVE:RuleState.SUPPORTED,RuleState.SUPPORTED:RuleState.CONFIRMED}.get(current.state)
                if next_state: rule = staged_rules.transition(rule_id,next_state,evidence_id)
        if rule is not None:
            derived.append(CanonicalRecord.create(RecordType.RULE_RECORD,scope,{"rule_id":rule.rule_id,"version":rule.version,"statement":rule.statement,"state":rule.state.value,"predecessor_id":rule.predecessor_id,"conditions":rule.conditions},provenance=(evidence_id,hypothesis_id),status=EpistemicStatus.INFERRED if rule.state not in {RuleState.CONTRADICTED,RuleState.DISPROVEN,RuleState.INVALIDATED} else EpistemicStatus.CONTRADICTED,independence_group=independence_group))

        base_records = (pre_record, action_commit, post_record, temporal_record, difference_record, *evidence, *derived)
        conclusion = None
        if conclusion_input:
            conclusion = self.conclusions.compile(scope, provenance=tuple(record.record_id for record in base_records), **conclusion_input)
            base_records += (conclusion,)
        record_ids = tuple(record.record_id for record in base_records)
        probabilities = {key: belief.probability for key,belief in staged_hypotheses.beliefs.items()}
        rule_states = {key: versions[-1].state.value for key,versions in staged_rules.versions.items()}
        snapshot = KnowledgeSnapshot.seal(scope.game_id, scope.episode_id, scope.cycle, record_ids, (pre_record.record_id,post_record.record_id), tuple(record.record_id for record in evidence), probabilities, rule_states, (conclusion.record_id,) if conclusion else (), self.uncertainty.get(scope.game_id,{"mechanics":1.0}), scope.context_signature)
        snapshot_record = CanonicalRecord.create(RecordType.KNOWLEDGE_SNAPSHOT, scope, {"snapshot_id": snapshot.snapshot_id, "knowledge_digest": snapshot.knowledge_digest, "record_ids": snapshot.record_ids}, provenance=record_ids, status=EpistemicStatus.INFERRED, independence_group=independence_group)

        # No projection mutates until one durable transaction contains the entire cycle.
        transaction = self.log.commit((*base_records, snapshot_record))
        self.hypotheses = staged_hypotheses; self.rules = staged_rules
        for record in transaction.records: self.records[record.record_id] = record
        self.snapshots[scope.game_id] = snapshot
        return snapshot

    def readonly_records(self) -> Mapping[str, CanonicalRecord]:
        from types import MappingProxyType
        return MappingProxyType(self.records)
