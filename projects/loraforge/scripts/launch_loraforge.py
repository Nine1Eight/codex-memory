#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "loraforge.config.json"


def main() -> int:
    if not CONFIG.exists():
        print(f"Missing config: {CONFIG}")
        return 1

    cfg = json.loads(CONFIG.read_text())
    print("LORAForge workspace loaded")
    print(f"workspace: {cfg['workspace']}")
    print(f"base_models: {cfg['paths']['base_models']}")
    print(f"datasets: {cfg['paths']['datasets']}")
    print(f"adapters: {cfg['paths']['adapters']}")
    print("\nNext: place a base model in models/base and datasets in datasets/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
