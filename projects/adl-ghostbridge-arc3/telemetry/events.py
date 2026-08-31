from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class Telemetry:
    def __init__(self, path: str | Path = "logs/agent.jsonl") -> None:
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def emit(self, event: str, **data: Any) -> None:
        with self.path.open("a", encoding="utf-8") as stream: stream.write(json.dumps({"event": event, **data}, sort_keys=True, default=str) + "\n")
