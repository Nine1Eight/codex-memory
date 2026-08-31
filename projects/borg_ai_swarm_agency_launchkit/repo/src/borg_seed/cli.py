from __future__ import annotations

import argparse
import json
from pathlib import Path

from .capsule import create_borg_archive, inspect_borg_archive


def main() -> int:
    parser = argparse.ArgumentParser(prog="borg-seed")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create")
    p_create.add_argument("--out", default="dist/borg-agent-seed.borg")
    p_create.add_argument("--name", default="borg-agent-seed")

    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("path")

    args = parser.parse_args()

    if args.cmd == "create":
        out = create_borg_archive(Path(args.out), name=args.name)
        print(json.dumps(inspect_borg_archive(out), indent=2, sort_keys=True))
        return 0

    if args.cmd == "inspect":
        print(json.dumps(inspect_borg_archive(Path(args.path)), indent=2, sort_keys=True))
        return 0

    raise SystemExit(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
