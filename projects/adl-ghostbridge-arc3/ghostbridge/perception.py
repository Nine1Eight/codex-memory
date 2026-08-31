from __future__ import annotations

from collections import Counter
from typing import Any

from .schemas import ImmutableObservation


class BudgetedPerception:
    def cheap(self, observation: ImmutableObservation) -> dict[str, Any]:
        colors = Counter(value for row in observation.frame for value in row)
        return {"frame_hash": observation.frame_hash, "shape": (len(observation.frame), max((len(row) for row in observation.frame), default=0)), "palette": tuple(sorted(colors)), "counts": dict(colors)}

    def needs_expensive(self, before: dict[str, Any], after: dict[str, Any], score_delta: float = 0.0) -> bool:
        return bool(score_delta or before.get("shape") != after.get("shape") or before.get("counts") != after.get("counts"))

