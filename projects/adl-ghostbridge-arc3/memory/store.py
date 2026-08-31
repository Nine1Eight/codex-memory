from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from prl.sid import SemanticIDDecoder
from world.state import Reflection, WorldState


class MemoryStore:
    def __init__(self, path: str | Path = "checkpoints/memory.json") -> None:
        self.path = Path(path); self.data: dict[str, Any] = {"games": {}, "levels": {}, "reflections": []}
        if self.path.exists(): self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def update(self, reflection: Reflection) -> None:
        self.data["reflections"].append({"outcome": reflection.outcome.value, "action": reflection.prediction.action.action_id, "error": reflection.prediction_error, "score_value": reflection.score_value})
        self.data["reflections"] = self.data["reflections"][-1000:]

    def commit_level(self, world: WorldState) -> None:
        self.data["levels"][f"{world.identity.full_id}:{world.level}"] = self._summary(world); self._save()

    def commit_game(self, world: WorldState) -> None:
        self.data["games"][world.identity.full_id] = self._summary(world); self._save()

    @staticmethod
    def _summary(world: WorldState) -> dict[str, Any]:
        return {"fingerprint": asdict(world.fingerprint) if world.fingerprint else None, "level": world.level, "progress": world.progress, "entities": [(e.kind, e.color, len(e.cells)) for e in world.entities], "topology": world.topology, "actions": [a.action_id for a in world.available_actions]}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True); temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8"); temporary.replace(self.path)
