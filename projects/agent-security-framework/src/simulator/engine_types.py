"""Structural protocols kept separate to avoid runtime import cycles."""

from __future__ import annotations

from typing import Any, Protocol


class ActionLike(Protocol):
    @property
    def parameters(self) -> dict[str, Any]: ...

    @property
    def provenance(self) -> tuple[str, ...]: ...
