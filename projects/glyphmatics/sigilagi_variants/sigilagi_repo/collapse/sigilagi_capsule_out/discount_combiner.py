from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Dict, Any


@dataclass(frozen=True)
class DiscountRule:
    name: str
    kind: str
    value: float
    priority: int = 100
    exclusive_group: str | None = None
    stackable: bool = True


class DiscountCombiner:
    """
    Deterministic discount engine.

    Supported rule kinds:
    - percent: value = percentage in [0, 100]
    - fixed:   value = fixed currency deduction
    """

    def __init__(self, rules: Iterable[DiscountRule] | None = None) -> None:
        self.rules: List[DiscountRule] = sorted(list(rules or []), key=lambda r: (r.priority, r.name))

    def add_rule(self, rule: DiscountRule) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: (r.priority, r.name))

    def combine(self, subtotal: float) -> Dict[str, Any]:
        if subtotal < 0:
            raise ValueError("subtotal must be non-negative")

        applied: List[Dict[str, Any]] = []
        running = float(subtotal)
        used_groups: set[str] = set()

        for rule in self.rules:
            if rule.exclusive_group and rule.exclusive_group in used_groups:
                continue

            before = running
            if rule.kind == "percent":
                delta = round(running * (rule.value / 100.0), 2)
                running = max(0.0, round(running - delta, 2))
            elif rule.kind == "fixed":
                delta = min(round(rule.value, 2), running)
                running = round(running - delta, 2)
            else:
                raise ValueError(f"unsupported rule kind: {rule.kind}")

            if delta > 0:
                applied.append(
                    {
                        "name": rule.name,
                        "kind": rule.kind,
                        "value": rule.value,
                        "before": round(before, 2),
                        "discount": round(delta, 2),
                        "after": round(running, 2),
                    }
                )
                if rule.exclusive_group:
                    used_groups.add(rule.exclusive_group)
                if not rule.stackable:
                    break

        return {
            "subtotal": round(subtotal, 2),
            "final_total": round(running, 2),
            "total_discount": round(subtotal - running, 2),
            "applied": applied,
        }
