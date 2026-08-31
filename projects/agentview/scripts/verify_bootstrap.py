from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", action="store_true")
    parser.add_argument("--lint", action="store_true")
    parser.add_argument("--typecheck", action="store_true")
    parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    required = [
        "AGENTS.md",
        "README.md",
        "LICENSE",
        "Makefile",
        ".env.example",
        "apps/api/agentview_api/main.py",
        "docs/AGENTVIEW_EXECPLAN.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        raise SystemExit(f"missing required files: {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
