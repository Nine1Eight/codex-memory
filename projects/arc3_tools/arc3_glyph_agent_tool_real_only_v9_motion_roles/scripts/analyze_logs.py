#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, Iterator, Any

def iter_events(path: Path) -> Iterator[Dict[str, Any]]:
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.glob("*.jsonl"))
    for file in files:
        with file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    event["_file"] = str(file)
                    yield event
                except json.JSONDecodeError:
                    continue

def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path("logs")
    events = list(iter_events(target))
    if not events:
        print(f"No JSONL events found in {target}")
        return 0

    by_game = defaultdict(list)
    mode_counts = Counter()
    action_counts = Counter()

    for event in events:
        by_game[str(event.get("game_id", "unknown"))].append(event)
        mode_counts[str(event.get("mode", "unknown"))] += 1
        action_counts[str(event.get("selected_action", "unknown"))] += 1

    print("Events:", len(events))
    print("Games:", len(by_game))

    print("\nModes:")
    for k, v in mode_counts.most_common():
        print(f"  {k}: {v}")

    print("\nActions:")
    for k, v in action_counts.most_common():
        print(f"  {k}: {v}")

    print("\nPer game:")
    for game, rows in sorted(by_game.items()):
        last = rows[-1]
        print(
            f"  {game}: steps={len(rows)} "
            f"last_mode={last.get('mode')} last_action={last.get('selected_action')}"
        )

    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
