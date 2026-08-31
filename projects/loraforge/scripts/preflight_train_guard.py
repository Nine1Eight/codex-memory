#!/usr/bin/env python3
"""
Preflight guard for real LoRA training jobs.

This script does not fabricate datasets, models, labels, or training outputs.
It verifies that explicitly provided input paths exist before a training runner
is allowed to start.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional


def require_path(label: str, value: str, *, must_be_dir: Optional[bool] = None) -> Path:
    p = Path(value).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"Missing {label}: {p}")
    if must_be_dir is True and not p.is_dir():
        raise SystemExit(f"{label} must be a directory: {p}")
    if must_be_dir is False and not p.is_file():
        raise SystemExit(f"{label} must be a file: {p}")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", required=True, help="Path to local base model directory")
    ap.add_argument("--dataset", required=True, help="Path to real dataset file or directory")
    ap.add_argument("--output-dir", required=True, help="Adapter output directory")
    args = ap.parse_args()

    base = require_path("base model", args.base_model, must_be_dir=True)
    dataset = require_path("dataset", args.dataset, must_be_dir=None)
    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    print("Preflight OK")
    print(f"base_model={base}")
    print(f"dataset={dataset}")
    print(f"output_dir={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
