#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import Counter

def iter_jsonl(path: Path):
    files = [path] if path.is_file() else sorted(path.glob("*.jsonl"))
    for f in files:
        with f.open("r", encoding="utf-8", errors="ignore") as h:
            for line in h:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    e["_file"] = str(f)
                    yield e
                except Exception:
                    pass

def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path("logs")
    events = list(iter_jsonl(target))
    reflected = [e for e in events if e.get("mode") == "budgeted_reflection_plan"]
    progress = [e for e in events if e.get("mode") == "verified_progress_plan"]
    modes = Counter(str(e.get("mode", "unknown")) for e in events)

    print("events:", len(events))
    print("modes:")
    for k, v in modes.most_common():
        print(f"  {k}: {v}")

    print("verified_progress_plan events:", len(progress))

    if not reflected:
        print("no budgeted_reflection_plan events found")
        return 0

    last = reflected[-1]
    print("\nreflection events:", len(reflected))
    print("last budget:", last.get("reflection_budget"))
    print("last selected:", last.get("selected_sequence"))
    print("last start_distance:", last.get("start_distance"))
    print("last candidates:")
    for c in last.get("candidate_plans", [])[:8]:
        print(" ", c)

    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
