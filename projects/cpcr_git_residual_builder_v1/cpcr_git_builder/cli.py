from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapter_io import package_adapter_zip, validate_adapter_dir, validate_submission_zip, validation_report, write_test_adapter
from .corpus import build_residual_rows, generate_seed_git_rows, read_prompts_csv, write_jsonl, write_report


def main() -> int:
    ap = argparse.ArgumentParser(prog="cpcr-git", description="CPCR-GIT Residual Adapter Builder v1")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("generate-seed-corpus")
    p.add_argument("--out-jsonl", required=True)
    p.add_argument("--report", default=None)

    p = sub.add_parser("build-residual-corpus")
    p.add_argument("--prompts-csv", required=True)
    p.add_argument("--out-jsonl", required=True)
    p.add_argument("--report", default=None)
    p.add_argument("--include-quarantine-verified", action="store_true")

    p = sub.add_parser("write-test-adapter")
    p.add_argument("--adapter-dir", required=True)
    p.add_argument("--rank", type=int, default=8)
    p.add_argument("--hidden", type=int, default=64)

    p = sub.add_parser("validate-adapter")
    p.add_argument("--adapter-dir", required=True)
    p.add_argument("--max-rank", type=int, default=32)

    p = sub.add_parser("package-adapter")
    p.add_argument("--adapter-dir", required=True)
    p.add_argument("--out-zip", required=True)
    p.add_argument("--max-rank", type=int, default=32)

    p = sub.add_parser("validate-submission")
    p.add_argument("--zip", required=True)
    p.add_argument("--max-rank", type=int, default=32)

    args = ap.parse_args()

    if args.cmd == "generate-seed-corpus":
        rows = generate_seed_git_rows()
        stats = write_jsonl(rows, Path(args.out_jsonl), allowed_only=True)
        if args.report:
            write_report(stats, Path(args.report))
        print(json.dumps({"ok": True, "rows": stats.total, "written_allowed": stats.train_allowed}, indent=2))
        return 0

    if args.cmd == "build-residual-corpus":
        prompts = read_prompts_csv(Path(args.prompts_csv))
        rows = build_residual_rows(prompts, include_quarantine_verified=args.include_quarantine_verified)
        stats = write_jsonl(rows, Path(args.out_jsonl), allowed_only=True)
        if args.report:
            write_report(stats, Path(args.report))
        print(json.dumps({"ok": True, "rows": stats.total, "written_allowed": stats.train_allowed, "quarantined": stats.quarantined}, indent=2))
        return 0

    if args.cmd == "write-test-adapter":
        write_test_adapter(args.adapter_dir, rank=args.rank, hidden=args.hidden)
        v = validate_adapter_dir(args.adapter_dir)
        print(validation_report(v))
        v.assert_ok()
        return 0

    if args.cmd == "validate-adapter":
        v = validate_adapter_dir(args.adapter_dir, max_rank=args.max_rank)
        print(validation_report(v))
        v.assert_ok()
        return 0

    if args.cmd == "package-adapter":
        v = package_adapter_zip(args.adapter_dir, args.out_zip, max_rank=args.max_rank)
        print(validation_report(v))
        return 0

    if args.cmd == "validate-submission":
        v = validate_submission_zip(args.zip, max_rank=args.max_rank)
        print(validation_report(v))
        v.assert_ok()
        return 0

    raise AssertionError(args.cmd)

if __name__ == "__main__":
    raise SystemExit(main())
