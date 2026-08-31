from __future__ import annotations

from typing import Any, Callable, Mapping

from .schemas import CanonicalRecord, EpistemicStatus, ExperimentProposal, GhostBridgeForecast, RecordType, Scope, ValueVector, digest
from .scoring import products


class RHAECommitGateway:
    """The only component authorized to turn candidates into one real action."""

    def choose(self, scope: Scope, proposals: tuple[ExperimentProposal,...], forecasts: tuple[GhostBridgeForecast,...], mode="explore"):
        by_id={item.proposal_id:item for item in forecasts}; ranked=[]
        for proposal in proposals:
            forecast=by_id[proposal.proposal_id]
            vector=ValueVector(forecast.progress_probability,forecast.reward_probability,forecast.reachability_delta,forecast.reversibility,forecast.snapshot_digest==forecast.snapshot_digest,proposal.epistemic_value,proposal.epistemic_value,proposal.epistemic_value,1.0-forecast.failure_probability,forecast.failure_probability,forecast.reversibility)
            value=products(vector,mode); ranked.append((value.decision_utility,proposal.proposal_id,proposal,forecast,value))
        if not ranked: raise RuntimeError("RHAE has no legal candidates")
        return max(ranked)

    def commit_external(self, scope: Scope, action: str, data: Mapping[str,Any], legal_actions: tuple[str,...], *, committer="RHAE") -> CanonicalRecord:
        if action not in legal_actions: raise ValueError(f"illegal committed action {action}")
        payload={"action":action,"data":dict(data),"committer":committer,"exactly_one":True}
        return CanonicalRecord.create(RecordType.ACTION_COMMIT,scope,payload,status=EpistemicStatus.OBSERVED,independence_group=f"episode:{scope.episode_id}:transition:{scope.transition_id}")
