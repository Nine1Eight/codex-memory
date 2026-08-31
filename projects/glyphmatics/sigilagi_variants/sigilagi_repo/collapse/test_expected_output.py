#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict


def load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_demo(tree: Path) -> Dict[str, Any]:
    if str(tree) not in sys.path:
        sys.path.insert(0, str(tree))
    mod = load_module(tree / "sigil_stack.py", "sigil_stack_runtime")
    stack = mod.SigilAGIStack()
    return stack.demo()


def assert_expected(result: Dict[str, Any]) -> None:
    if "rag_hits" not in result or not result["rag_hits"]:
        raise AssertionError("missing rag_hits")
    if result["rag_hits"][0]["doc_id"] != "sigil-rag":
        raise AssertionError(f"unexpected top rag hit: {result['rag_hits'][0]['doc_id']}")

    refined = result.get("refined")
    if not isinstance(refined, dict):
        raise AssertionError("missing refined block")
    if refined.get("change_count") != 3:
        raise AssertionError(f"unexpected change_count: {refined.get('change_count')}")

    pricing = result.get("pricing")
    if pricing is not None:
        if pricing.get("final_total") != 107.5:
            raise AssertionError(f"unexpected pricing.final_total: {pricing.get('final_total')}")
        if pricing.get("total_discount") != 17.5:
            raise AssertionError(f"unexpected pricing.total_discount: {pricing.get('total_discount')}")

    recommendations = result.get("recommendations")
    if recommendations is not None:
        if not isinstance(recommendations, list) or not recommendations:
            raise AssertionError("recommendations exists but is empty/invalid")


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert expected deterministic output for source and rehydrated trees")
    parser.add_argument("--source", required=True, help="Original source directory")
    parser.add_argument("--rehydrated", required=True, help="Rehydrated output directory")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    rehydrated = Path(args.rehydrated).expanduser().resolve()

    source_result = run_demo(source)
    rehydrated_result = run_demo(rehydrated)

    assert_expected(source_result)
    assert_expected(rehydrated_result)

    if source_result != rehydrated_result:
        raise AssertionError("source result and rehydrated result differ")

    print(json.dumps({
        "ok": True,
        "source_result": source_result,
        "rehydrated_result": rehydrated_result,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
