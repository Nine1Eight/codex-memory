#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def iter_records(root: Path):
    for path in sorted(root.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"Bad JSON in {path}:{line_number}: {exc}") from exc
                yield path.name, record


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("nine18_memory")
    if not root.exists():
        print(json.dumps({"root": str(root), "records": 0, "games": {}}, indent=2))
        return 0

    games: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "records": 0,
        "actions": Counter(),
        "states": Counter(),
        "max_levels_completed": 0,
        "reward_values": [],
        "changed": 0,
        "unique_fingerprints": set(),
    })
    for filename, record in iter_records(root):
        game_id = str(record.get("game_id") or filename.removesuffix(".jsonl"))
        bucket = games[game_id]
        bucket["records"] += 1
        action_id = record.get("action_id")
        if action_id is not None:
            bucket["actions"][str(action_id)] += 1
        bucket["states"][str(record.get("state", ""))] += 1
        bucket["max_levels_completed"] = max(bucket["max_levels_completed"], int(record.get("levels_completed") or 0))
        bucket["reward_values"].append(float(record.get("reward") or 0.0))
        if record.get("changed"):
            bucket["changed"] += 1
        fp = record.get("fingerprint")
        if fp:
            bucket["unique_fingerprints"].add(str(fp))

    output: dict[str, Any] = {"root": str(root), "records": 0, "games": {}}
    for game_id, bucket in sorted(games.items()):
        rewards = bucket["reward_values"]
        output["records"] += bucket["records"]
        output["games"][game_id] = {
            "records": bucket["records"],
            "max_levels_completed": bucket["max_levels_completed"],
            "changed_rate": round(bucket["changed"] / max(1, bucket["records"]), 6),
            "unique_fingerprints": len(bucket["unique_fingerprints"]),
            "actions": dict(sorted(bucket["actions"].items(), key=lambda kv: int(kv[0]))),
            "states": dict(bucket["states"]),
            "reward_mean": round(statistics.fmean(rewards), 6) if rewards else 0.0,
            "reward_max": round(max(rewards), 6) if rewards else 0.0,
        }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
