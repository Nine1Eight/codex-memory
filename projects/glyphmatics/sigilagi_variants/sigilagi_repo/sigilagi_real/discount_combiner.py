from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(order=True)
class DiscountRule:
    priority: int
    name: str
    kind: str
    value: float


class DiscountCombiner:
    def __init__(self) -> None:
        self.rules: List[DiscountRule] = []

    def add_rule(self, rule: DiscountRule) -> None:
        self.rules.append(rule)
        self.rules.sort()

    def combine(self, subtotal: float) -> Dict[str, Any]:
        applied = []
        current = float(subtotal)

        for rule in self.rules:
            before = current
            if rule.kind == "percent":
                discount = round(before * (rule.value / 100.0), 2)
            elif rule.kind == "fixed":
                discount = min(round(rule.value, 2), before)
            else:
                raise ValueError(f"unsupported discount kind: {rule.kind}")

            current = round(before - discount, 2)
            applied.append({
                "name": rule.name,
                "kind": rule.kind,
                "value": rule.value,
                "before": before,
                "discount": discount,
                "after": current,
            })

        return {
            "subtotal": round(subtotal, 2),
            "final_total": current,
            "total_discount": round(subtotal - current, 2),
            "applied": applied,
        }
