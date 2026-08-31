from __future__ import annotations
from typing import Dict, Any

from retrieval_index import RetrievalIndex
from registry_manifest import RegistryManifest


class QueryEngine:
    def __init__(self, retrieval: RetrievalIndex, registry: RegistryManifest) -> None:
        self.retrieval = retrieval
        self.registry = registry

    def run(self, query: str, top_k: int = 3, include_registry: bool = True) -> Dict[str, Any]:
        hits = self.retrieval.search(query, top_k=top_k)
        out: Dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "hits": hits,
            "hit_count": len(hits),
        }
        if include_registry:
            out["registry"] = self.registry.snapshot()
        return out
