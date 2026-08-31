from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .normalizers import boxed, normalize_answer
from .routing import infer_category, route_category, sort_rows_cpcr
from .solvers import solve_any

@dataclass
class CorpusStats:
    total: int = 0
    train_allowed: int = 0
    verified: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)
    by_stage: Dict[str, int] = field(default_factory=dict)
    quarantined: int = 0

    def add(self, row: dict) -> None:
        self.total += 1
        self.train_allowed += int(bool(row.get("train_allowed")))
        self.verified += int(bool(row.get("verified")))
        cat = row.get("category", "unknown")
        stage = str(row.get("cpcr_stage", "?"))
        self.by_category[cat] = self.by_category.get(cat, 0) + 1
        self.by_stage[stage] = self.by_stage.get(stage, 0) + 1
        if not row.get("train_allowed"):
            self.quarantined += 1


def make_git_row(prompt: str, answer: Any, category: Optional[str] = None, verified: bool = True, source: str = "git") -> dict:
    category = category or infer_category(prompt)
    route = route_category(category, verified=verified)
    return {
        "instruction": "Answer the problem. Return only the final boxed answer.",
        "input": prompt,
        "output": boxed(answer),
        "prompt": prompt,
        "answer": normalize_answer(answer),
        "category": route.category,
        "verified": verified,
        "confidence": route.confidence_prior,
        "source": source,
        "cpcr_stage": route.stage,
        "train_allowed": route.train_allowed,
        "route_reason": route.reason,
        "meta": {"format": "direct_boxed_answer"},
    }


def generate_seed_git_rows() -> List[dict]:
    prompts = [
        "What is 7 * 12?",
        "Convert binary 101101 to decimal.",
        "Convert decimal 45 to binary.",
        "Convert 3 km to meter.",
        "Compute 6 << 2.",
        "Solve cryptarithm A + A = B. What is B?",
        "On Earth, what is the weight in newtons if mass is 5 kg?",
    ]
    rows = []
    for p in prompts:
        solved = solve_any(p)
        if solved is not None:
            rows.append(solved.row(p, source="seed_solver_git"))
    return sort_rows_cpcr(rows)


def build_residual_rows(prompts: Iterable[str], include_quarantine_verified: bool = True) -> List[dict]:
    rows: List[dict] = []
    for prompt in prompts:
        solved = solve_any(prompt)
        if solved is None:
            # Unknowns remain ledger-only, not training rows.
            cat = infer_category(prompt)
            route = route_category(cat, verified=False)
            rows.append({
                "instruction": "Answer the problem. Return only the final boxed answer.",
                "input": prompt,
                "output": "",
                "prompt": prompt,
                "answer": "",
                "category": route.category,
                "verified": False,
                "confidence": route.confidence_prior,
                "source": "unsolved_residual_ledger",
                "cpcr_stage": route.stage,
                "train_allowed": False,
                "route_reason": route.reason,
                "meta": {"status": "unsolved"},
            })
        else:
            row = solved.row(prompt, source="residual_verified_solver")
            route = route_category(row["category"], verified=solved.verified)
            row.update({
                "cpcr_stage": route.stage,
                "train_allowed": route.train_allowed,
                "route_reason": route.reason,
            })
            if row["train_allowed"] or include_quarantine_verified:
                rows.append(row)
    return sort_rows_cpcr(rows)


def read_prompts_csv(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        prompt_col = next((c for c in ["prompt", "question", "input", "problem"] if c in cols), None)
        if prompt_col is None:
            raise ValueError(f"could not find prompt column in {path}; columns={cols}")
        return [row[prompt_col] for row in reader if row.get(prompt_col)]


def write_jsonl(rows: Iterable[dict], out_path: Path, allowed_only: bool = True) -> CorpusStats:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stats = CorpusStats()
    with out_path.open("w", encoding="utf-8") as f:
        for row in sort_rows_cpcr(rows):
            stats.add(row)
            if allowed_only and not row.get("train_allowed"):
                continue
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return stats


def write_report(stats: CorpusStats, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asdict(stats), indent=2, sort_keys=True), encoding="utf-8")
