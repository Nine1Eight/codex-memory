from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json


class CorpusLoader:
    def __init__(self, corpus_path: str | Path) -> None:
        self.corpus_path = Path(corpus_path).expanduser().resolve()

    def load(self) -> List[Dict[str, Any]]:
        if not self.corpus_path.exists():
            raise FileNotFoundError(f"missing corpus file: {self.corpus_path}")

        data = json.loads(self.corpus_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise TypeError("corpus must be a JSON list")

        docs: List[Dict[str, Any]] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise TypeError(f"corpus item {i} is not an object")
            if "doc_id" not in item or "text" not in item:
                raise ValueError(f"corpus item {i} missing doc_id or text")

            docs.append({
                "doc_id": str(item["doc_id"]),
                "text": str(item["text"]),
                "metadata": dict(item.get("metadata", {})),
            })

        docs.sort(key=lambda x: x["doc_id"])
        return docs
