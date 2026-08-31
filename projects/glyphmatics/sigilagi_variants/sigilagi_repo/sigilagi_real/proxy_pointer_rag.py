from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class Doc:
    doc_id: str
    text: str
    metadata: Dict[str, Any]


class ProxyPointerRAG:
    def __init__(self) -> None:
        self.docs: List[Doc] = []

    def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any]) -> None:
        self.docs.append(Doc(doc_id, text, metadata))

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        q_terms = [t for t in query.lower().split() if t]
        scored = []

        for doc in self.docs:
            d_terms = doc.text.lower().split()
            overlap = sum(1 for t in q_terms if t in d_terms)
            score = round(overlap / max(len(q_terms), 1), 6)
            if score > 0:
                scored.append({
                    "doc_id": doc.doc_id,
                    "score": score,
                    "snippet": doc.text[:111],
                    "metadata": doc.metadata,
                    "proxy_pointer": f"{doc.doc_id}#0:{min(len(doc.text), 111)}",
                })

        scored.sort(key=lambda x: (-x["score"], x["doc_id"]))
        return scored[:top_k]
