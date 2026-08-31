from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import threading
from typing import Any

from .schemas import EvidenceRecord, TransitionEnvelope, canonical


class EvidenceLedger:
    """Append-only evidence store with atomic transition commits."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.records: dict[str, EvidenceRecord] = {}
        self.transitions: list[TransitionEnvelope] = []
        self._lock = threading.RLock()

    def append(self, record: EvidenceRecord) -> str:
        with self._lock:
            existing = self.records.get(record.record_id)
            if existing is not None and existing != record:
                raise ValueError(f"immutable evidence collision: {record.record_id}")
            missing = [parent for parent in record.parents if parent not in self.records and not parent.startswith(("obs-", "act-", "del-", "eve-", "pre-", "tra-"))]
            if missing:
                raise ValueError(f"unknown evidence parents: {missing}")
            self.records[record.record_id] = record
            return record.record_id

    def commit(self, envelope: TransitionEnvelope) -> str:
        envelope.verify()
        with self._lock:
            if any(item.transition_id == envelope.transition_id for item in self.transitions):
                return envelope.transition_id
            if self.transitions and self.transitions[-1].game_id == envelope.game_id and self.transitions[-1].step >= envelope.step:
                raise ValueError("non-monotonic transition commit")
            self.transitions.append(envelope)
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                line = canonical(envelope.to_dict()) + "\n"
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
                    handle.flush()
            return envelope.transition_id

    def replay_digest(self) -> str:
        payload = [item.to_dict() for item in self.transitions]
        return sha256(canonical(payload).encode()).hexdigest()

    @classmethod
    def replay(cls, path: str | Path) -> "EvidenceLedger":
        from .integration import envelope_from_dict
        ledger = cls(path=None)
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                ledger.commit(envelope_from_dict(json.loads(line)))
        return ledger

