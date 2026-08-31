from __future__ import annotations

from dataclasses import dataclass

from .state import Entity


@dataclass(slots=True)
class EntityMatch:
    entity: Entity
    support: float

