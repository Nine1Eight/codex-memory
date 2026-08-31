from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import json


class IndexedLoader:
    def __init__(self, index_path: str | Path) -> None:
        self.index_path = Path(index_path).expanduser().resolve()

    def load(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            raise FileNotFoundError(f"missing index file: {self.index_path}")

        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError("index must be a JSON object")

        required = {"doc_count", "term_count", "docs", "inverted_index"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"index missing keys: {sorted(missing)}")

        return data
