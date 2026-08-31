from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from typing import Any

from packages.domain import AgentViewReceipt, ReceiptPayload, ReceiptSignature


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def make_receipt(receipt_id: str, payload: ReceiptPayload, signature: ReceiptSignature) -> AgentViewReceipt:
    return AgentViewReceipt(
        schema_version="agentview.receipt.v1",
        receipt_id=receipt_id,
        payload=payload,
        signature=signature,
    )


def receipt_to_json(receipt: AgentViewReceipt) -> dict[str, object]:
    return json.loads(json.dumps(_plain(receipt), sort_keys=True))

