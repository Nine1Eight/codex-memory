from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType
from typing import Mapping

from .schemas import CanonicalRecord, CausalLevel, ExperimentProposal, GhostBridgeForecast, KnowledgeSnapshot, RecordType, digest


class GhostBridgeWorldModel:
    """Predictive owner. Cannot write ADL evidence, confidence, or rules."""

    def __init__(self) -> None:
        self._snapshots: dict[str,KnowledgeSnapshot] = {}; self._snapshot: KnowledgeSnapshot | None = None; self._records: Mapping[str,CanonicalRecord] = MappingProxyType({})
        self._action_effects: dict[str, dict[str,int]] = defaultdict(lambda: defaultdict(int)); self._action_trials: dict[str,int] = defaultdict(int)

    def publish(self, snapshot: KnowledgeSnapshot, records: Mapping[str,CanonicalRecord]) -> None:
        previous = self._snapshots.get(snapshot.game_id)
        if previous and snapshot.cycle < previous.cycle: raise ValueError("cannot publish an older snapshot")
        if any(record_id not in records for record_id in snapshot.record_ids): raise ValueError("snapshot references unavailable ADL evidence")
        self._snapshot = snapshot; self._snapshots[snapshot.game_id] = snapshot; self._records = MappingProxyType(dict(records))
        # Rebuild forecasts exclusively from sealed observed records.
        action = None
        for record_id in snapshot.record_ids:
            record = records[record_id]
            if record.record_type == RecordType.ACTION_COMMIT: action = str(record.payload["action"]); self._action_trials[action] += 1
            elif action and record.record_type == RecordType.EVIDENCE_EVENT:
                self._action_effects[action][str(record.payload.get("event_type","unknown"))] += 1

    def forecast(self, proposals: tuple[ExperimentProposal,...]) -> tuple[GhostBridgeForecast,...]:
        if self._snapshot is None: raise RuntimeError("GhostBridge requires a sealed KnowledgeSnapshot")
        output = []
        for proposal in proposals:
            trials = max(1,self._action_trials[proposal.action]); effects = self._action_effects[proposal.action]
            predicted = tuple(sorted(kind for kind,count in effects.items() if count/trials >= 0.35))
            reward = effects.get("reward",0)/trials; progress = (effects.get("progress",0)+effects.get("reward",0))/trials
            body = {"proposal":proposal.proposal_id,"snapshot":self._snapshot.knowledge_digest,"predicted":predicted,"trials":trials}
            level = CausalLevel.OBSERVED_ASSOCIATION if trials <= 1 else CausalLevel.REPEATED_ASSOCIATION if trials <= 2 else CausalLevel.INTERVENTION_SUPPORTED
            output.append(GhostBridgeForecast(proposal.proposal_id,predicted,min(1.0,progress),min(1.0,reward),0.0,0.05 if trials==1 else effects.get("failure",0)/trials,proposal.reversibility,"pre-"+digest(body)[:24],self._snapshot.knowledge_digest,level))
        return tuple(output)
