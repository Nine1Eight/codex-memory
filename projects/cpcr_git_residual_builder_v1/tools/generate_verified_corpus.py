#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cpcr_git_builder.corpus import build_residual_rows, write_jsonl


def dedup_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for x in items:
        x = " ".join(str(x).strip().split())
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def make_equation_prompts(limit: int) -> list[str]:
    prompts = []
    for a in range(2, 80):
        for b in range(2, 80):
            prompts.append(f"What is {a} + {b}?")
            prompts.append(f"What is {a} * {b}?")
            prompts.append(f"Calculate {a} + {b}.")
            prompts.append(f"Compute {a} * {b}.")
            if len(prompts) >= limit:
                return dedup_keep_order(prompts)[:limit]
    return dedup_keep_order(prompts)[:limit]


def make_numeral_prompts(limit: int) -> list[str]:
    prompts = []
    for n in range(1, 512):
        prompts.append(f"Convert decimal {n} to binary.")
        prompts.append(f"Convert binary {n:b} to decimal.")
        if len(prompts) >= limit:
            return dedup_keep_order(prompts)[:limit]
    return dedup_keep_order(prompts)[:limit]


def make_unit_prompts(limit: int) -> list[str]:
    prompts = []
    for n in range(1, 512):
        prompts.append(f"Convert {n} km to meter.")
        prompts.append(f"Convert {n} hour to minute.")
        if len(prompts) >= limit:
            return dedup_keep_order(prompts)[:limit]
    return dedup_keep_order(prompts)[:limit]


def make_bit_prompts(limit: int) -> list[str]:
    prompts = []
    for a in range(1, 512):
        for b in range(1, 64):
            shift = b % 8
            prompts.append(f"Compute {a} << {shift}.")
            prompts.append(f"Compute {a} >> {shift}.")
            prompts.append(f"Compute bitwise xor {a} and {b}.")
            prompts.append(f"Compute bitwise or {a} with {b}.")
            prompts.append(f"Compute {a} & {b}.")
            prompts.append(f"Compute {a} | {b}.")
            prompts.append(f"What is {a} ^ {b}?")
            if len(dedup_keep_order(prompts)) >= limit * 2:
                return dedup_keep_order(prompts)[:limit]
    return dedup_keep_order(prompts)[:limit]


def make_gravity_prompts(limit: int) -> list[str]:
    prompts = []
    for m in range(1, 512):
        prompts.append(f"On Earth, what is the weight in newtons if mass is {m} kg?")
        prompts.append(f"What is the weight in newtons on Earth for mass {m} kg?")
        if len(prompts) >= limit:
            return dedup_keep_order(prompts)[:limit]
    return dedup_keep_order(prompts)[:limit]


def make_cryptarithm_prompts(limit: int) -> list[str]:
    forms = [
        "Solve cryptarithm A + A = B. What is B?",
        "In the cryptarithm A + A = B, what is B?",
        "For cryptarithm A + A = B, give B.",
        "Cryptarithm: A + A = B. What digit is B?",
    ]
    prompts = []
    for i in range(max(limit, len(forms))):
        prompts.append(forms[i % len(forms)] + f" Variant {i}.")
    return dedup_keep_order(prompts)[:limit]


def build_prompts(equation: int, numeral: int, unit: int, bit: int, gravity: int, cryptarithm: int) -> list[str]:
    prompts = []
    prompts.extend(make_equation_prompts(equation))
    prompts.extend(make_numeral_prompts(numeral))
    prompts.extend(make_unit_prompts(unit))
    prompts.extend(make_bit_prompts(bit))
    prompts.extend(make_gravity_prompts(gravity))
    prompts.extend(make_cryptarithm_prompts(cryptarithm))
    return dedup_keep_order(prompts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-jsonl", default="build/verified_train_v1_2.jsonl")
    ap.add_argument("--out-prompts-csv", default="build/verified_prompts_v1_2.csv")
    ap.add_argument("--summary", default="build/verified_summary_v1_2.json")
    ap.add_argument("--equation", type=int, default=300)
    ap.add_argument("--numeral", type=int, default=300)
    ap.add_argument("--unit", type=int, default=300)
    ap.add_argument("--bit", type=int, default=250)
    ap.add_argument("--gravity", type=int, default=150)
    ap.add_argument("--cryptarithm", type=int, default=25)
    args = ap.parse_args()

    prompts = build_prompts(args.equation, args.numeral, args.unit, args.bit, args.gravity, args.cryptarithm)

    Path(args.out_prompts_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_prompts_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["prompt"])
        for p in prompts:
            w.writerow([p])

    rows = build_residual_rows(prompts, include_quarantine_verified=True)
    stats = write_jsonl(rows, Path(args.out_jsonl), allowed_only=True)

    train = [r for r in rows if r.get("train_allowed")]
    summary = {
        "ok": True,
        "requested_prompt_count": len(prompts),
        "total_solver_rows": len(rows),
        "written_allowed": stats.train_allowed,
        "category_counts": dict(sorted(Counter(r["category"] for r in train).items())),
        "stage_counts": dict(sorted(Counter(str(r["cpcr_stage"]) for r in train).items())),
        "out_jsonl": args.out_jsonl,
        "out_prompts_csv": args.out_prompts_csv,
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
