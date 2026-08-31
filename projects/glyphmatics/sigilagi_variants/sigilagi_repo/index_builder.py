from __future__ import annotations
from typing import Dict, Any, List


class IndexBuilder:
    @staticmethod
    def tokenize(text: str) -> List[str]:
        return [tok.strip(".,:;!?()[]{}\"'").lower() for tok in text.split() if tok.strip()]

    def build(self, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            for term in self.tokenize(text):
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
