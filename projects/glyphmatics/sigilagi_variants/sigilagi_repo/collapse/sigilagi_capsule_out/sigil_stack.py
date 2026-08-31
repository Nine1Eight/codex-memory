from __future__ import annotations
from typing import Dict, Any
import json

from discount_combiner import DiscountCombiner, DiscountRule
from proxy_pointer_rag import ProxyPointerRAG
from system_refiner import SystemRefiner
from enhancement_discovery import EnhancementDiscovery


class SigilAGIStack:
    """
    Minimal deterministic orchestration layer that proves the capsule
    can rehydrate executable modules, import them, and perform work.
    """

    def __init__(self) -> None:
        self.combiner = DiscountCombiner()
        self.rag = ProxyPointerRAG()
        self.refiner = SystemRefiner()
        self.discovery = EnhancementDiscovery()

    def load_demo_state(self) -> None:
        self.combiner.add_rule(DiscountRule(name="launch10", kind="percent", value=10.0, priority=10))
        self.combiner.add_rule(DiscountRule(name="vip5", kind="fixed", value=5.0, priority=20))

        self.rag.add_document(
            "glyph-core",
            "GlyphMatics core focuses on deterministic symbolic execution, anchored registries, and reproducible transforms.",
            {"layer": "core"},
        )
        self.rag.add_document(
            "sigil-rag",
            "Proxy pointer RAG uses stable retrieval over indexed documents and returns precise anchor ranges for expansion.",
            {"layer": "retrieval"},
        )
        self.rag.add_document(
            "refiner",
            "System refinement merges config deltas into a canonical stack manifest while preserving a change log.",
            {"layer": "control"},
        )

    def demo(self) -> Dict[str, Any]:
        self.load_demo_state()

        pricing = self.combiner.combine(125.00)
        rag_hits = self.rag.search("deterministic retrieval anchor config", top_k=2)
        refined = self.refiner.refine(
            {"mode": "seed", "layers": {"core": True, "apps": False}},
            {"mode": "expanded", "layers": {"apps": True}, "boot": {"verified": True}},
        )
        recommendations = self.discovery.discover(
            {
                "doc_count": len(self.rag.docs),
                "discount_rule_count": len(self.combiner.rules),
                "change_count": refined["change_count"],
            }
        )

        return {
            "pricing": pricing,
            "rag_hits": rag_hits,
            "refined": refined,
            "recommendations": recommendations,
        }


def main() -> int:
    stack = SigilAGIStack()
    result = stack.demo()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
