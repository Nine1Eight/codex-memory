from __future__ import annotations

from typing import Any


class CounterfactualEngine:
    def compare(self, predictions: dict[Any, dict[str, float]]) -> tuple[Any, Any] | None:
        ranked = sorted(predictions, key=lambda action: (-float(predictions[action].get("information", 0.0)), str(action)))
        return tuple(ranked[:2]) if len(ranked) >= 2 else None

    def discriminating_action(self, left: dict[Any, set[str]], right: dict[Any, set[str]]) -> Any | None:
        candidates = sorted(set(left) | set(right), key=str)
        return max(candidates, key=lambda action: len(left.get(action,set()) ^ right.get(action,set())), default=None)

