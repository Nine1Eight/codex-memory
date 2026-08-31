from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from .authority import ADLAuthority
from .ghostbridge_model import GhostBridgeWorldModel
from .rdl_boundary import RDLBoundary
from .rhae_gateway import RHAECommitGateway
from .schemas import CanonicalRecord, EvidenceVector, KnowledgeSnapshot, Scope, canonical, digest
from .transaction_log import TransactionLog


def _frame(snapshot: Mapping[str,Any]):
    value=snapshot.get("grid") or snapshot.get("frame") or ()
    if hasattr(value,"tolist"): value=value.tolist()
    return tuple(tuple(int(cell) for cell in row) for row in value) if value and isinstance(value,(list,tuple)) and isinstance(value[0],(list,tuple)) else ()


def _difference(pre: Mapping[str,Any],post: Mapping[str,Any]):
    left,right=_frame(pre),_frame(post); height=max(len(left),len(right)); width=max(max((len(x) for x in left),default=0),max((len(x) for x in right),default=0)); changes=[]
    for y in range(height):
        for x in range(width):
            before=left[y][x] if y<len(left) and x<len(left[y]) else None; after=right[y][x] if y<len(right) and x<len(right[y]) else None
            if before!=after: changes.append((x,y,before,after))
    score_delta=float(post.get("score") or 0)-float(pre.get("score") or 0); level_delta=int(post.get("levels") or post.get("level") or 0)-int(pre.get("levels") or pre.get("level") or 0)
    return {"changed_cells":tuple(changes),"score_delta":score_delta,"level_delta":level_delta,"pre_digest":digest(pre),"post_digest":digest(post)}


class ADLVNextCoordinator:
    def __init__(self, path=None) -> None:
        self.log=TransactionLog(path); self.adl=ADLAuthority(self.log); self.ghostbridge=GhostBridgeWorldModel(); self.rhae=RHAECommitGateway(); self.rdl=RDLBoundary(); self.cycles:dict[str,int]={}; self.episodes:dict[str,str]={}; self._prepared:dict[str,tuple[Scope,CanonicalRecord]]={}

    def advisory(self,game_id:str,legal_actions:tuple[tuple[str,Mapping[str,Any]],...],episode_id:str|None=None):
        snapshot=self.adl.snapshots.get(game_id)
        if snapshot is None:
            episode_id=episode_id or self.episodes.setdefault(game_id,f"{game_id}:episode:1")
            snapshot=KnowledgeSnapshot.seal(game_id,episode_id,self.cycles.get(game_id,0),(),(),(),{}, {},(),{"mechanics":1.0},f"{game_id}|bootstrap")
            self.ghostbridge.publish(snapshot,{})
        proposals=self.adl.propose_experiments(snapshot,legal_actions); forecasts=self.ghostbridge.forecast(proposals)
        return {"snapshot_id":snapshot.snapshot_id,"knowledge_digest":snapshot.knowledge_digest,"proposals":proposals,"forecasts":forecasts}

    def prepare_external_action(self,game_id:str,action:Any,pre:Mapping[str,Any],*,legal_actions:tuple[str,...]|None=None,episode_id:str|None=None):
        if game_id in self._prepared or self.rdl.debt(game_id): raise RuntimeError("adl_debt blocks next action")
        cycle=self.cycles.get(game_id,0)+1; episode_id=episode_id or self.episodes.setdefault(game_id,f"{game_id}:episode:1")
        action_name=str(getattr(action,"id",getattr(action,"action_id",action.get("id") if isinstance(action,Mapping) else action))); action_data=dict(getattr(action,"data",{}) or (action.get("data",{}) if isinstance(action,Mapping) else {}))
        transition_id="trn-"+digest({"game":game_id,"episode":episode_id,"cycle":cycle,"action":action_name,"data":action_data,"pre":digest(pre)})[:24]
        context=f"{game_id}|L{int(pre.get('levels') or pre.get('level') or 0)}|actions:{','.join(sorted(legal_actions or (action_name,)))}"
        scope=Scope(game_id,episode_id,cycle,transition_id,context); action_commit=self.rhae.commit_external(scope,action_name,action_data,legal_actions or (action_name,),committer="TAAF_RHAE")
        self.rdl.begin(scope,action_commit,pre); self._prepared[game_id]=(scope,action_commit)
        return {"scope":scope,"action_commit":action_commit}

    def complete_external_action(self,game_id:str,post:Mapping[str,Any],*,runtime_boundary_complete=True)->KnowledgeSnapshot:
        if game_id not in self._prepared: raise RuntimeError("successful action has no ActionCommit")
        scope,action_commit=self._prepared[game_id]; pending=self.rdl.pending[game_id]; pre=pending.pre
        self.rdl.observe(game_id,post,runtime_boundary_complete=runtime_boundary_complete); pending,normalized_post,temporal=self.rdl.settle(game_id)
        difference=_difference(pre,normalized_post); event_type="reward" if difference["score_delta"]>0 or difference["level_delta"]>0 else "progress" if difference["changed_cells"] else "no_observed_effect"
        positive=event_type in {"reward","progress"}; vector=EvidenceVector(1.0,1.0,0.75,0.9 if temporal["stabilized"] else 0.55,1.0,0.8)
        evidence=({"event_type":event_type,"polarity":"positive" if positive else "negative","expected_result":{},"observed_result":difference,"attribution":{"action_commit_id":action_commit.record_id},"evidence_vector":dict(zip(("detection","reliability","semantic","temporal","independence","novelty"),vector.values())),"likelihood_given_h":0.8 if positive else 0.2,"likelihood_given_not_h":0.25 if positive else 0.75,"dependence_discount":1.0,"temporal_discount":vector.temporal,"context_discount":1.0},)
        conclusion_input={"move":event_type,"sequence":"single committed transition","mechanic":"unresolved" if not positive else "candidate action effect","strategy":"continue experiment" if not positive else "verify nearby reward path","game":"active","partitions":{"known":(action_commit.record_id,),"probable":(),"unknown":(),"contradicted":(),"disproven":()},"supporting":(action_commit.record_id,),"contradictory":(),"alternatives":("latent temporal effect",),"assumptions":("runtime boundary complete",),"falsification_tests":({"repeat_action":action_commit.payload["action"]},),"strategic_implications":("RHAE retains action authority",),"ranked_experiments":(),"failure_class":"unresolved_mechanic"}
        snapshot=self.adl.ingest(scope,pre={"frame":_frame(pre),"score":pre.get("score",0),"level":pre.get("levels",pre.get("level",0))},action_commit=action_commit,post={"frame":_frame(normalized_post),"score":normalized_post.get("score",0),"level":normalized_post.get("levels",normalized_post.get("level",0))},difference=difference,temporal=temporal,evidence_inputs=evidence,conclusion_input=conclusion_input)
        self.ghostbridge.publish(snapshot,self.adl.readonly_records()); self.cycles[game_id]=scope.cycle; del self._prepared[game_id]
        if self.rdl.debt(game_id): raise RuntimeError("adl_debt did not return to zero")
        return snapshot

    def record_external_action(self,game_id:str,action:Any,pre:Mapping[str,Any],post:Mapping[str,Any],*,legal_actions:tuple[str,...]|None=None,episode_id:str|None=None,runtime_boundary_complete=True)->KnowledgeSnapshot:
        self.prepare_external_action(game_id,action,pre,legal_actions=legal_actions,episode_id=episode_id)
        return self.complete_external_action(game_id,post,runtime_boundary_complete=runtime_boundary_complete)
