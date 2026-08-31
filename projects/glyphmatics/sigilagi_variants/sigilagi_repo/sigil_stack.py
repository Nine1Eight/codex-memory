from __future__ import annotations
from typing import Dict, Any
import json
from pathlib import Path

from system_refiner import SystemRefiner
from discount_combiner import DiscountCombiner, DiscountRule
from enhancement_discovery import EnhancementDiscovery
from registry_manifest import RegistryManifest
from indexed_loader import IndexedLoader
from retrieval_index import RetrievalIndex
from query_engine import QueryEngine


class SigilAGIStack:
    def __init__(self) -> None:
        self.refiner = SystemRefiner()
        self.combiner = DiscountCombiner()
        self.discovery = EnhancementDiscovery()
        self.registry = RegistryManifest()
        self.base_dir = Path(__file__).resolve().parent
        self.retrieval = None
        self.query_engine = None

    def load_demo_state(self) -> None:
        index_snapshot = IndexedLoader(self.base_dir / "index.json").load()
        self.retrieval = RetrievalIndex(index_snapshot)

        self.combiner.add_rule(DiscountRule(priority=10, name="launch10", kind="percent", value=10.0))
        self.combiner.add_rule(DiscountRule(priority=20, name="vip5", kind="fixed", value=5.0))

        self.registry.register_modules([
            "system_refiner.py",
            "discount_combiner.py",
            "enhancement_discovery.py",
            "registry_manifest.py",
            "indexed_loader.py",
            "retrieval_index.py",
            "query_engine.py",
            "sigil_stack.py",
            "corpus.json",
            "index.json",
        ])
        self.registry.apply_state(
            boot_verified=True,
            rehydrated=True,
            indexed=True,
            persisted_index=True,
            query_ready=True,
        )

        self.query_engine = QueryEngine(self.retrieval, self.registry)

    def run_query(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        self.load_demo_state()
        retrieval = self.query_engine.run(query=query, top_k=top_k, include_registry=True)

        refined = self.refiner.refine(
            {"mode": "seed", "layers": {"core": True, "apps": False}},
            {"mode": "expanded", "layers": {"apps": True}, "boot": {"verified": True}},
        )
        pricing = self.combiner.combine(125.0)
        recommendations = self.discovery.discover(
            {
                "doc_count": len(self.retrieval.snapshot["docs"]),
                "discount_rule_count": len(self.combiner.rules),
                "change_count": refined["change_count"],
            }
        )

        return {
            "retrieval": retrieval,
            "refined": refined,
            "pricing": pricing,
            "recommendations": recommendations,
            "index": {
                "doc_count": self.retrieval.snapshot["doc_count"],
                "term_count": self.retrieval.snapshot["term_count"],
            },
        }

    def demo(self) -> Dict[str, Any]:
        return self.run_query("deterministic retrieval anchor config", top_k=2)


def main() -> int:
    result = SigilAGIStack().demo()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
