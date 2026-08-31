#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from discount_combiner import DiscountCombiner, DiscountRule
from enhancement_discovery import EnhancementDiscovery
from indexed_loader import IndexedLoader
from registry_manifest import RegistryManifest
from retrieval_index import RetrievalIndex


def build_index_from_corpus(corpus_path: Path) -> Dict[str, Any]:
    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError("corpus must be a JSON list")

    docs: Dict[str, Dict[str, Any]] = {}
    inverted: Dict[str, List[str]] = {}

    def tokenize(text: str) -> List[str]:
        return [tok.strip(".,:;!?()[]{}\"'").lower() for tok in text.split() if tok.strip()]

    for i, item in enumerate(sorted(data, key=lambda x: str(x.get("doc_id", "")))):
        if not isinstance(item, dict):
            raise TypeError(f"corpus item {i} is not an object")
        if "doc_id" not in item or "text" not in item:
            raise ValueError(f"corpus item {i} missing doc_id or text")

        doc_id = str(item["doc_id"])
        text = str(item["text"])
        metadata = dict(item.get("metadata", {}))
        docs[doc_id] = {"text": text, "metadata": metadata}

        seen = set()
        for term in tokenize(text):
            if term in seen:
                continue
            seen.add(term)
            inverted.setdefault(term, []).append(doc_id)

    for term in inverted:
        inverted[term] = sorted(inverted[term])

    return {
        "doc_count": len(docs),
        "term_count": len(inverted),
        "docs": docs,
        "inverted_index": inverted,
    }


def render_text(result: Dict[str, Any], show_registry: bool, show_pricing: bool, show_refined: bool) -> str:
    lines = []

    retrieval = result["retrieval"]
    lines.append(f'Query: {retrieval["query"]}')
    lines.append(f'Top K: {retrieval["top_k"]}')
    lines.append(f'Hits: {retrieval["hit_count"]}')
    lines.append("")

    for i, hit in enumerate(retrieval["hits"], 1):
        lines.append(f'[{i}] {hit["doc_id"]}  score={hit["score"]}')
        lines.append(f'    layer: {hit["metadata"].get("layer", "")}')
        lines.append(f'    ptr  : {hit["proxy_pointer"]}')
        lines.append(f'    text : {hit["snippet"]}')
        lines.append("")

    if show_pricing and "pricing" in result:
        pricing = result["pricing"]
        lines.append("Pricing")
        lines.append(f'  subtotal      : {pricing["subtotal"]}')
        lines.append(f'  final_total   : {pricing["final_total"]}')
        lines.append(f'  total_discount: {pricing["total_discount"]}')
        lines.append("")

    if show_refined and "refined" in result:
        refined = result["refined"]
        lines.append("Refined")
        lines.append(f'  change_count: {refined["change_count"]}')
        lines.append("")

    if show_registry and "registry" in retrieval:
        registry = retrieval["registry"]
        lines.append("Registry")
        lines.append(f'  system : {registry["system"]}')
        lines.append(f'  version: {registry["version"]}')
        lines.append(f'  slice  : {registry["slice"]}')
        lines.append(f'  modules: {len(registry["modules"])}')
        lines.append("")

    if "index" in result:
        index = result["index"]
        lines.append("Index")
        lines.append(f'  doc_count : {index["doc_count"]}')
        lines.append(f'  term_count: {index["term_count"]}')

    return "\n".join(lines).rstrip() + "\n"


def run_local_query(query: str, top_k: int, corpus: str | None, index: str | None) -> Dict[str, Any]:
    registry = RegistryManifest()

    if corpus:
        corpus_path = Path(corpus).expanduser().resolve()
        snapshot = build_index_from_corpus(corpus_path)
        registry.register_modules([corpus_path.name, "query_cli.py"])
        registry.apply_state(
            boot_verified=False,
            rehydrated=False,
            indexed=True,
            persisted_index=False,
            query_ready=True,
            external_corpus=True,
        )
    else:
        if index:
            index_path = Path(index).expanduser().resolve()
        else:
            index_path = Path(__file__).resolve().parent / "index.json"
        snapshot = IndexedLoader(index_path).load()
        registry.register_modules([index_path.name, "query_cli.py"])
        registry.apply_state(
            boot_verified=False,
            rehydrated=False,
            indexed=True,
            persisted_index=True,
            query_ready=True,
            external_corpus=False,
        )

    retrieval = RetrievalIndex(snapshot)
    retrieval_block = {
        "query": query,
        "top_k": top_k,
        "hits": retrieval.search(query, top_k=top_k),
        "hit_count": len(retrieval.search(query, top_k=top_k)),
        "registry": registry.snapshot(),
    }

    combiner = DiscountCombiner()
    combiner.add_rule(DiscountRule(priority=10, name="launch10", kind="percent", value=10.0))
    combiner.add_rule(DiscountRule(priority=20, name="vip5", kind="fixed", value=5.0))
    pricing = combiner.combine(125.0)

    discovery = EnhancementDiscovery()
    recommendations = discovery.discover(
        {
            "doc_count": snapshot["doc_count"],
            "discount_rule_count": len(combiner.rules),
            "change_count": 3,
        }
    )

    refined = {
        "config": {
            "mode": "expanded",
            "layers": {"core": True, "apps": True},
            "boot": {"verified": True},
        },
        "changes": [
            {"op": "replace", "path": "mode", "before": "seed", "after": "expanded"},
            {"op": "replace", "path": "layers.apps", "before": False, "after": True},
            {"op": "add", "path": "boot", "value": {"verified": True}},
        ],
        "change_count": 3,
    }

    return {
        "retrieval": retrieval_block,
        "refined": refined,
        "pricing": pricing,
        "recommendations": recommendations,
        "index": {
            "doc_count": snapshot["doc_count"],
            "term_count": snapshot["term_count"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="SigilAGI query CLI")
    parser.add_argument("query", help="Query string")
    parser.add_argument("--top-k", type=int, default=3, help="Number of hits to return")
    parser.add_argument("--corpus", help="Path to external corpus.json")
    parser.add_argument("--index", help="Path to external index.json")
    parser.add_argument("--json", action="store_true", help="Emit full JSON")
    parser.add_argument("--show-registry", action="store_true", help="Show registry summary in text mode")
    parser.add_argument("--show-pricing", action="store_true", help="Show pricing summary in text mode")
    parser.add_argument("--show-refined", action="store_true", help="Show refinement summary in text mode")
    args = parser.parse_args()

    if args.corpus and args.index:
        raise SystemExit("use either --corpus or --index, not both")

    result = run_local_query(args.query, args.top_k, args.corpus, args.index)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(
            result,
            show_registry=args.show_registry,
            show_pricing=args.show_pricing,
            show_refined=args.show_refined,
        ), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
