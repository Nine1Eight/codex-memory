from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import compact_actions


@dataclass
class KnownRoute:
    game_id: str
    root: str
    level: int | None
    sequence_index: str
    actions: list[dict[str, Any]]
    compact: str
    route_type: str
    enabled: bool = False


class KnownSequenceArchive:
    """
    Diagnostic known-sequence archive. Disabled unless --use-known-sequences is set.
    Gating is conservative: exact full game_id first, then root only when explicitly allowed.
    """

    def __init__(self, path: str | Path, enable: bool = False, allow_root_alias: bool = False):
        self.path = Path(path)
        self.enable = bool(enable)
        self.allow_root_alias = bool(allow_root_alias)
        self.routes = self._load()

    def _load(self) -> list[KnownRoute]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        routes = []
        for row in raw.get("routes", []):
            actions = row.get("raw") or [{"action": a, "data": None} for a in row.get("action_ids", [])]
            aids = [int(a.get("action", a.get("id", 0))) for a in actions]
            routes.append(KnownRoute(
                game_id=str(row.get("game_id", "")),
                root=str(row.get("root", str(row.get("game_id", "")).split("-")[0])),
                level=row.get("level"),
                sequence_index=str(row.get("sequence_index", "0")),
                actions=actions,
                compact=str(row.get("compact") or compact_actions(aids)),
                route_type=str(row.get("type", "unknown")),
                enabled=False,
            ))
        return routes

    def list_routes(self, enabled_only: bool = False) -> list[KnownRoute]:
        if enabled_only and not self.enable:
            return []
        return self.routes if not enabled_only else [r for r in self.routes if self.enable]

    def route_for(self, game_id: str, level: int) -> KnownRoute | None:
        if not self.enable:
            return None
        root = game_id.split("-")[0]
        exact = [r for r in self.routes if r.game_id == game_id and (r.level is None or int(r.level) == int(level))]
        if exact:
            exact.sort(key=lambda r: (r.level is None, len(r.actions)))
            return exact[0]
        if not self.allow_root_alias:
            return None
        alias = [r for r in self.routes if r.root == root and (r.level is None or int(r.level) == int(level))]
        if alias:
            alias.sort(key=lambda r: (r.level is None, len(r.actions)))
            return alias[0]
        return None
