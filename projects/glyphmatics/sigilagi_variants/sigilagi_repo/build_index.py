#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List


def tokenize(text: str) -> List[str]:
    return [tok.strip(".,:;!?()[]{}\"'").lower() for tok in text.split() if tok.strip()]


def build_index(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    inverted: Dict[str, List[str]] = {}
    doc_store: Dict[str, Dict[str, Any]] = {}

    for doc in sorted(docs, key=lambda d: d["doc_id"]):
        doc_id = str(doc["doc_id"])
        text = str(doc["text"])
        metadata = dict(doc.get("metadata", {}))
        doc_store[doc_id] = {
            "text": text,
            "metadata": metadata,
        }

        seen_terms = set()
        for term in tokenize(text):
            if term in seen_terms:
                continue
            seen_terms.add(term)
            inverted.setdefault(term, []).append(doc_id)

    for term in inverted:
        inverted[term] = sorted(inverted[term])

    return {
        "doc_count": len(doc_store),
        "term_count": len(inverted),
        "docs": doc_store,
        "inverted_index": inverted,
    }


def main() -> int:
    base = Path(__file__).resolve().parent
    corpus_path = base / "corpus.json"
    out_path = base / "index.json"

    if not corpus_path.exists():
        raise FileNotFoundError(f"missing corpus file: {corpus_path}")

    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError("corpus must be a JSON list")

    docs = []
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

    snapshot = build_index(docs)

    out_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
