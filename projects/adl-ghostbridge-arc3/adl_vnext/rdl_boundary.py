from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .schemas import CanonicalRecord, EpistemicStatus, RecordType, Scope, digest


@dataclass(slots=True)
class PendingBoundary:
    scope: Scope
    action_commit: CanonicalRecord
    pre: Mapping[str,Any]
    observations: list[Mapping[str,Any]] = field(default_factory=list)


class RDLBoundary:
    """Owns alignment and stability only; emits no semantic conclusions."""

    def __init__(self, stable_observations=2, deadline_observations=8) -> None:
        self.stable_observations=stable_observations; self.deadline_observations=deadline_observations; self.pending: dict[str,PendingBoundary]={}

    def begin(self, scope: Scope, action_commit: CanonicalRecord, pre: Mapping[str,Any]) -> None:
        if scope.game_id in self.pending: raise RuntimeError("adl_debt blocks next action")
        if action_commit.record_type != RecordType.ACTION_COMMIT: raise TypeError("RDL requires ActionCommit")
        self.pending[scope.game_id]=PendingBoundary(scope,action_commit,dict(pre))

    def observe(self, game_id: str, observation: Mapping[str,Any], *, runtime_boundary_complete=False) -> bool:
        pending=self.pending[game_id]; pending.observations.append(dict(observation)); hashes=[digest(x.get("frame",x.get("grid",()))) for x in pending.observations[-self.stable_observations:]]
        stable=len(hashes)>=self.stable_observations and len(set(hashes))==1
        deadline=len(pending.observations)>=self.deadline_observations
        return stable or deadline or runtime_boundary_complete or bool(observation.get("terminal"))

    def settle(self, game_id: str) -> tuple[PendingBoundary,Mapping[str,Any],dict[str,Any]]:
        pending=self.pending.pop(game_id)
        if not pending.observations: raise RuntimeError("POST observation missing")
        post=pending.observations[-1]
        temporal={"observation_count":len(pending.observations),"observation_digests":tuple(digest(x) for x in pending.observations),"stabilized":len(pending.observations)>=self.stable_observations,"deadline_expired":len(pending.observations)>=self.deadline_observations,"action_commit_id":pending.action_commit.record_id}
        return pending,post,temporal

    def debt(self,game_id:str)->int: return int(game_id in self.pending)
