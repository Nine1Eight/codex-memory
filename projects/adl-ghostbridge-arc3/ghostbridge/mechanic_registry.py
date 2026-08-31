from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Mechanic:
    name: str
    preconditions: frozenset[str]
    action: str
    effects: frozenset[str]
    support_contexts: set[str] = field(default_factory=set)
    contradiction_contexts: set[str] = field(default_factory=set)

    @property
    def verified(self) -> bool:
        return len(self.support_contexts) >= 2 and not self.contradiction_contexts


class MechanicRegistry:
    def __init__(self) -> None:
        self.mechanics: dict[str, Mechanic] = {}

    def record(self, mechanic: Mechanic) -> None:
        self.mechanics[mechanic.name] = mechanic

    def verified(self) -> tuple[Mechanic, ...]:
        return tuple(item for item in self.mechanics.values() if item.verified)
