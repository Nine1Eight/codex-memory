from __future__ import annotations

from .schemas import KnowledgeSnapshot, RecordType
from .transaction_log import TransactionLog


class KnowledgeReplay:
    def replay(self, log: TransactionLog) -> dict[str,KnowledgeSnapshot]:
        snapshots={}; hypotheses:dict[str,dict[str,float]]={}; rules:dict[str,dict[str,str]]={}
        for transaction in log.transactions:
            records=transaction.records; snapshot_records=[r for r in records if r.record_type==RecordType.KNOWLEDGE_SNAPSHOT]
            if len(snapshot_records)!=1: raise ValueError("each cycle transaction requires one KnowledgeSnapshot")
            marker=snapshot_records[0]; scope=marker.scope; base=tuple(r for r in records if r.record_type!=RecordType.KNOWLEDGE_SNAPSHOT)
            hp=hypotheses.setdefault(scope.game_id,{})
            for record in base:
                if record.record_type in {RecordType.HYPOTHESIS_RECORD,RecordType.CONTRADICTION_RECORD}: hp[str(record.payload["hypothesis_id"])]=float(record.payload["probability"])
            rp=rules.setdefault(scope.game_id,{})
            for record in base:
                if record.record_type==RecordType.RULE_RECORD: rp[str(record.payload["rule_id"])]=str(record.payload["state"])
            observations=tuple(r.record_id for r in base if r.record_type==RecordType.OBSERVATION_SNAPSHOT); evidence=tuple(r.record_id for r in base if r.record_type==RecordType.EVIDENCE_EVENT); conclusions=tuple(r.record_id for r in base if r.record_type==RecordType.CONCLUSION_BUNDLE)
            snapshot=KnowledgeSnapshot.seal(scope.game_id,scope.episode_id,scope.cycle,tuple(r.record_id for r in base),observations,evidence,hp,rp,conclusions,{"mechanics":1.0},scope.context_signature)
            if snapshot.snapshot_id!=marker.payload["snapshot_id"] or snapshot.knowledge_digest!=marker.payload["knowledge_digest"]: raise ValueError("KnowledgeSnapshot deterministic replay mismatch")
            snapshots[scope.game_id]=snapshot
        return snapshots

    def from_path(self,path): return self.replay(TransactionLog.replay(path))
