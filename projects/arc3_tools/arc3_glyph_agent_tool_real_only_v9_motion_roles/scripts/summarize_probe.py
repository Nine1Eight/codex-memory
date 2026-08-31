#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

def load_events(path: Path):
    files = [path] if path.is_file() else sorted(path.glob("frame_probe_*.jsonl"))
    for f in files:
        with f.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    event["_file"] = str(f)
                    yield event
                except Exception:
                    pass

def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path("logs")
    events = list(load_events(target))
    if not events:
        print(f"No frame_probe_*.jsonl found in {target}")
        return 0

    for e in events[:20]:
        print("=" * 88)
        print("file:", e.get("_file"))
        print("step:", e.get("step"), "state:", e.get("state"), "frame:", e.get("frame_type"))
        print("grid:", e.get("grid_summary"))
        print("scene:", e.get("scene_summary"))
        fs = e.get("frame_summary", {})
        print("attrs:", fs.get("attrs"))
        vals = fs.get("values") or {}
        for k, v in vals.items():
            print(f"  {k}: {v}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
