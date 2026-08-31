from __future__ import annotations
from typing import Dict, Any, List


class RetrievalIndex:
    def __init__(self, snapshot: Dict[str, Any]) -> None:
        self.snapshot = snapshot
        self.docs = snapshot["docs"]
        self.inverted = snapshot["inverted_index"]

    @staticmethod
    def tokenize(text: str) -> List[str]:
        return [tok.strip(".,:;!?()[]{}\"'").lower() for tok in text.split() if tok.strip()]

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        terms = self.tokenize(query)
        scores: Dict[str, float] = {}

        for term in terms:
            for doc_id in self.inverted.get(term, []):
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0

        out: List[Dict[str, Any]] = []
        denom = max(len(terms), 1)
        for doc_id, raw_score in scores.items():
            doc = self.docs[doc_id]
            out.append({
                "doc_id": doc_id,
                "score": round(raw_score / denom, 6),
                "snippet": doc["text"][:111],
                "metadata": doc["metadata"],
                "proxy_pointer": f"{doc_id}#0:{min(len(doc['text']), 111)}",
            })

        out.sort(key=lambda x: (-x["score"], x["doc_id"]))
        return out[:top_k]
