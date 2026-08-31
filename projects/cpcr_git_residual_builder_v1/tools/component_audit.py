#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BOX_RE = re.compile(r"^\\boxed\{(.+)\}$")
DENY_ALWAYS = {"unknown", "equation_numeric_guess", "cryptarithm_guess"}
QUARANTINE_VERIFIED_ONLY = {"bit_manipulation"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row["__line__"] = i
            rows.append(row)
    return rows


def audit_rows(rows: list[dict[str, Any]], required_categories: set[str], min_rows: int) -> dict[str, Any]:
    errors = []
    warnings = []
    cats = Counter(str(r.get("category", "unknown")) for r in rows)
    stages = Counter(str(r.get("cpcr_stage", "?")) for r in rows)
    sources = Counter(str(r.get("source", "?")) for r in rows)
    by_cat_conf = defaultdict(list)

    if len(rows) < min_rows:
        errors.append(f"row_count {len(rows)} < min_rows {min_rows}")

    missing = sorted(required_categories - set(cats))
    if missing:
        errors.append(f"missing required categories: {missing}")

    last_stage = -1
    for r in rows:
        line = r.get("__line__", "?")
        cat = str(r.get("category", "unknown"))
        verified = bool(r.get("verified", False))
        train_allowed = bool(r.get("train_allowed", True))
        output = str(r.get("output", ""))
        answer = str(r.get("answer", ""))
        stage = int(r.get("cpcr_stage", 99))
        conf = float(r.get("confidence", r.get("confidence_prior", 0.0)) or 0.0)

        by_cat_conf[cat].append(conf)

        if stage < last_stage:
            errors.append(f"line {line}: CPCR order regressed: {stage} after {last_stage}")
        last_stage = stage

        if train_allowed and not verified:
            errors.append(f"line {line}: train_allowed row is not verified")
        if cat in DENY_ALWAYS:
            errors.append(f"line {line}: denylisted category leaked into train JSONL: {cat}")
        if cat in QUARANTINE_VERIFIED_ONLY and not verified:
            errors.append(f"line {line}: quarantine category {cat} is not verified")
        if train_allowed and not BOX_RE.match(output):
            errors.append(f"line {line}: train row output is not exactly boxed: {output!r}")
        if train_allowed and not answer:
            errors.append(f"line {line}: train row missing normalized answer")
        if conf <= 0:
            warnings.append(f"line {line}: non-positive confidence: {conf}")

    avg_conf = {
        cat: round(sum(vals) / len(vals), 6)
        for cat, vals in sorted(by_cat_conf.items())
        if vals
    }

    return {
        "ok": not errors,
        "row_count": len(rows),
        "category_counts": dict(sorted(cats.items())),
        "stage_counts": dict(sorted(stages.items())),
        "source_counts": dict(sorted(sources.items())),
        "avg_confidence_by_category": avg_conf,
        "required_categories": sorted(required_categories),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-rows", type=int, default=6)
    ap.add_argument("--required-categories", nargs="*", default=[])
    args = ap.parse_args()

    rows = load_jsonl(Path(args.jsonl))
    report = audit_rows(rows, set(args.required_categories), args.min_rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
