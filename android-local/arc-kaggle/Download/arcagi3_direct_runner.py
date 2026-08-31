from __future__ import annotations

import argparse
import json
from pathlib import Path

from multiverse_oracle.arcagi3 import ARCAGI3Policy, ARCEnvironmentRunner, ARCPolicyConfig


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Multiverse Oracle directly on an ARC-AGI-3 EnvironmentWrapper")
    parser.add_argument("--game", required=True, help="ARC-AGI-3 game id, e.g. ls20")
    parser.add_argument("--environments-dir", default="environment_files")
    parser.add_argument("--mode", choices=["normal", "online", "offline", "competition"], default="offline")
    parser.add_argument("--max-actions", type=int, default=400)
    parser.add_argument("--branches", type=int, default=96)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    try:
        import arc_agi
        from arc_agi import OperationMode
        from arcengine import GameAction
    except Exception as exc:
        raise SystemExit(
            "The official arc-agi/arcengine runtime is required for this runner. "
            "Install the competition-provided wheel or `arc-agi` package first."
        ) from exc

    mode_map = {
        "normal": OperationMode.NORMAL,
        "online": OperationMode.ONLINE,
        "offline": OperationMode.OFFLINE,
        "competition": OperationMode.COMPETITION,
    }
    arcade = arc_agi.Arcade(
        operation_mode=mode_map[args.mode],
        environments_dir=args.environments_dir,
    )
    env = arcade.make(args.game, render_mode="terminal-fast")
    if env is None:
        raise SystemExit(f"Could not create ARC-AGI-3 environment {args.game!r}")

    policy = ARCAGI3Policy(
        ARCPolicyConfig(branch_count=args.branches, horizon=args.horizon)
    )
    report = ARCEnvironmentRunner(policy, GameAction).run(env, max_actions=args.max_actions)
    scorecard = arcade.close_scorecard()
    if scorecard is not None:
        dump = getattr(scorecard, "model_dump", None)
        report["scorecard"] = dump() if callable(dump) else str(scorecard)

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
