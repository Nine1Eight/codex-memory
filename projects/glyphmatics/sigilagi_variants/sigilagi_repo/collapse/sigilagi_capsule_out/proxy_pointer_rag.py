from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Iterable
import math
import re


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


@dataclass
class Document:
    doc_id: str
    text: str
    metadata: Dict[str, Any]


class ProxyPointerRAG:
    """
    Deterministic lightweight RAG:
    - no external embeddings
    - stable bag-of-words TF cosine ranking
    - returns proxy pointers into top documents
    """

    def __init__(self, docs: Iterable[Document] | None = None) -> None:
        self.docs: List[Document] = list(docs or [])

    def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any] | None = None) -> None:
        self.docs.append(Document(doc_id=doc_id, text=text, metadata=dict(metadata or {})))

    @staticmethod
    def _tf(tokens: List[str]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        if not tokens:
            return out
        for tok in tokens:
            out[tok] = out.get(tok, 0.0) + 1.0
        n = float(len(tokens))
        for k in list(out):
            out[k] /= n
        return out

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        keys = set(a) | set(b)
        dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        q_tokens = _tokenize(query)
        q_tf = self._tf(q_tokens)
        scored: List[Dict[str, Any]] = []

        for doc in self.docs:
            d_tokens = _tokenize(doc.text)
            d_tf = self._tf(d_tokens)
            score = self._cosine(q_tf, d_tf)
            if score <= 0:
                continue

            snippet = doc.text[:220].replace("\n", " ").strip()
            scored.append(
                {
                    "doc_id": doc.doc_id,
                    "score": round(score, 6),
                    "snippet": snippet,
                    "metadata": doc.metadata,
                    "proxy_pointer": f"{doc.doc_id}#0:{min(len(doc.text), 220)}",
                }
            )

        scored.sort(key=lambda x: (-x["score"], x["doc_id"]))
        return scored[:top_k]
