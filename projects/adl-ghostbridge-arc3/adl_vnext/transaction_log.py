from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import threading
from typing import Iterable, Mapping

from .schemas import CanonicalRecord, canonical, record_from_dict


@dataclass(frozen=True, slots=True)
class LedgerTransaction:
    transaction_id: str
    sequence: int
    previous_digest: str
    records: tuple[CanonicalRecord, ...]
    digest: str

    def to_dict(self):
        return {"transaction_id": self.transaction_id, "sequence": self.sequence, "previous_digest": self.previous_digest, "records": [record.to_dict() for record in self.records], "digest": self.digest}


class TransactionLog:
    """Single durable source of truth; all domain ledgers are projections."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None; self.transactions: list[LedgerTransaction] = []; self._lock = threading.RLock()

    @property
    def head_digest(self) -> str:
        return self.transactions[-1].digest if self.transactions else "0" * 64

    def commit(self, records: Iterable[CanonicalRecord]) -> LedgerTransaction:
        records = tuple(records)
        if not records: raise ValueError("transaction requires records")
        for record in records: record.verify()
        with self._lock:
            sequence = len(self.transactions) + 1; previous = self.head_digest
            material = {"sequence": sequence, "previous_digest": previous, "record_digests": [record.canonical_digest for record in records]}
            tx_digest = sha256(canonical(material).encode()).hexdigest(); txid = f"txn-{tx_digest[:24]}"
            transaction = LedgerTransaction(txid, sequence, previous, records, tx_digest)
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                line = (canonical(transaction.to_dict()) + "\n").encode()
                descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                try:
                    written = os.write(descriptor, line)
                    if written != len(line): raise OSError("partial transaction append")
                    os.fsync(descriptor)
                finally: os.close(descriptor)
            self.transactions.append(transaction)
            return transaction

    @classmethod
    def replay(cls, path: str | Path) -> "TransactionLog":
        log = cls(None)
        for raw in Path(path).read_text(encoding="utf-8").splitlines():
            if not raw.strip(): continue
            item = json.loads(raw); records = tuple(record_from_dict(record) for record in item["records"])
            committed = log.commit(records)
            if committed.transaction_id != item["transaction_id"] or committed.digest != item["digest"]: raise ValueError("transaction replay digest mismatch")
        return log
