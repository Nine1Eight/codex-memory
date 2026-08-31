from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

from arcengine import GameState

from .env_loader import GameSpec, make_game, reset_game, select_games, step_game, project_root
from .known_sequences import KnownSequenceArchive
from .policy import Proposal, VoteLearnPolicy
from .recorder import ArtifactWriter
from .utils import diff_count, frame_array, frame_hash, write_json


def data_path(name: str) -> Path:
    return project_root() / "data" / name


def known_archive(args: argparse.Namespace) -> KnownSequenceArchive:
    return KnownSequenceArchive(
        data_path("known_sequences_catalog.json"),
        enable=bool(getattr(args, "use_known_sequences", False)),
        allow_root_alias=bool(getattr(args, "allow_root_alias", False)),
    )


def cmd_list_games(args: argparse.Namespace) -> int:
    for i, spec in enumerate(select_games(), 1):
        print(f"{i:02d} {spec.game_id:16s} root={spec.root:5s} tags={','.join(spec.tags) or '-'} actions={','.join(map(str, spec.baseline_actions[:8]))}")
    return 0


def cmd_list_known_sequences(args: argparse.Namespace) -> int:
    specs = select_games()
    exact_ids = {s.game_id for s in specs}
    roots = {s.root for s in specs}
    archive = known_archive(args)
    rows = []
    for r in archive.routes:
        exact = r.game_id in exact_ids
        alias = args.allow_root_alias and r.root in roots
        enabled = exact or alias
        if args.enabled_only and not enabled:
            continue
        rows.append((r.root, r.game_id, str(r.level), r.sequence_index, len(r.actions), "YES" if enabled else "no", r.compact[:90]))
    print(f"known_routes={len(rows)} exact_public_ids={sum(1 for r in archive.routes if r.game_id in exact_ids)} root_alias_allowed={args.allow_root_alias}")
    for row in rows:
        print("root={:<5s} game={:<16s} level={:<4s} seq={:<5s} len={:<3d} enabled={} :: {}".format(*row))
    return 0


def _state_name(frame: Any) -> str:
    try:
        return str(frame.state.value if hasattr(frame.state, "value") else frame.state)
    except Exception:
        return "unknown"


def _is_done(frame: Any) -> bool:
    try:
        return frame.state in (GameState.WIN, GameState.GAME_OVER)
    except Exception:
        return _state_name(frame) in {"WIN", "GAME_OVER", "win", "game_over"}


def _is_win(frame: Any) -> bool:
    try:
        return frame.state == GameState.WIN
    except Exception:
        return _state_name(frame).lower().endswith("win")


def _available(frame: Any, fallback: tuple[int, ...]) -> list[int]:
    try:
        a = list(getattr(frame, "available_actions", []) or [])
        if a:
            return [int(x) for x in a]
    except Exception:
        pass
    return [int(x) for x in fallback if int(x) > 0] or [1, 2, 3, 4, 5, 6]


def _proposal_from_known(route: Any, cursor: int) -> Proposal | None:
    if not route or cursor >= len(route.actions):
        return None
    row = route.actions[cursor]
    action = int(row.get("action", row.get("id", 0)))
    data = row.get("data")
    if action <= 0:
        return None
    return Proposal(
        action=action,
        data=data,
        confidence=1.0,
        source="known_sequence",
        reason=(
            f"known_route game={route.game_id} root={route.root} "
            f"level={route.level} seq={route.sequence_index} "
            f"cursor={cursor+1}/{len(route.actions)} type={route.route_type}"
        ),
    )


def run_one_game(spec: GameSpec, args: argparse.Namespace, writer: ArtifactWriter, archive: KnownSequenceArchive) -> dict[str, Any]:
    game = make_game(spec)
    policy = VoteLearnPolicy(seed=args.seed)
    frame = reset_game(game, spec.game_id)
    level = int(getattr(frame, "levels_completed", 0) or 0)
    max_steps = int(args.max_steps)
    known_route = None
    known_cursor = 0
    if args.use_known_sequences:
        known_route = archive.route_for(spec.game_id, level)

    stats = {
        "game_id": spec.game_id,
        "root": spec.root,
        "variant": spec.variant,
        "steps": 0,
        "episodes": 0,
        "best_levels": int(getattr(frame, "levels_completed", 0) or 0),
        "win_levels": int(getattr(frame, "win_levels", 0) or 0),
        "won": False,
        "error": None,
        "known_sequence_used": bool(known_route),
    }

    for step in range(max_steps):
        before = frame_array(frame)
        before_hash = frame_hash(before)
        prev_level = int(getattr(frame, "levels_completed", 0) or 0)
        available = _available(frame, spec.baseline_actions)

        known_route_before = known_route
        known_cursor_before = known_cursor
        known_action_attempted = False
        known_guard_rejected = False

        prop = _proposal_from_known(known_route, known_cursor) if known_route is not None else None
        if prop is not None:
            known_action_attempted = True
            known_cursor += 1
        else:
            known_route = None
            prop = policy.choose(before, spec.game_id, available, spec.tags)

        if prop.action not in available and available:
            # Hard guard. Some known archives use incompatible action maps.
            known_guard_rejected = bool(known_action_attempted)
            prop = policy.choose(before, spec.game_id, available, spec.tags)

        try:
            nxt = step_game(game, spec.game_id, prop.action, data=prop.data, reason=prop.reason)
        except Exception as e:
            row = {
                "game_id": spec.game_id,
                "step": step,
                "source": prop.source,
                "action": prop.action,
                "data": prop.data,
                "before_hash": before_hash,
                "error": repr(e),
            }
            writer.record_step(spec.game_id, row)
            raise

        after = frame_array(nxt)
        after_hash = frame_hash(after)
        new_level = int(getattr(nxt, "levels_completed", prev_level) or 0)
        level_delta = new_level - prev_level
        reward = float(level_delta)
        learn = policy.learn(before, after, prop.action, reward, level_delta, _is_done(nxt))
        delta = diff_count(before, after)
        route_info = None
        if known_route_before is not None:
            route_info = {
                "route_game_id": known_route_before.game_id,
                "route_root": known_route_before.root,
                "route_level": known_route_before.level,
                "route_sequence_index": known_route_before.sequence_index,
                "route_type": known_route_before.route_type,
                "route_len": len(known_route_before.actions),
                "route_compact": known_route_before.compact[:240],
                "used_as_root_alias": known_route_before.game_id != spec.game_id,
            }

        outcome_tags = list(learn.get("outcome_tags", [])) if isinstance(learn, dict) else []
        if level_delta > 0 and "level_advanced" not in outcome_tags:
            outcome_tags.append("level_advanced")
        if delta == 0 and "no_frame_change" not in outcome_tags:
            outcome_tags.append("no_frame_change")

        row = {
            "game_id": spec.game_id,
            "root": spec.root,
            "variant": spec.variant,
            "step": step,
            "level_before": prev_level,
            "level_after": new_level,
            "level_delta": level_delta,
            "win_levels": int(getattr(nxt, "win_levels", 0) or 0),
            "state": _state_name(nxt),
            "before_hash": before_hash,
            "after_hash": after_hash,
            "frame_delta": delta,
            "available_actions": available,
            "action": int(prop.action),
            "data": prop.data,
            "source": prop.source,
            "reason": prop.reason,
            "confidence": round(float(prop.confidence), 6),
            "reasoning": {
                "move_number": step + 1,
                "selected": {
                    "action": int(prop.action),
                    "data": prop.data,
                    "source": prop.source,
                    "confidence": round(float(prop.confidence), 6),
                    "reason": prop.reason,
                },
                "known_sequence": {
                    "enabled": bool(args.use_known_sequences),
                    "allow_root_alias": bool(args.allow_root_alias),
                    "active_before_move": bool(known_route_before is not None),
                    "attempted": bool(known_action_attempted),
                    "guard_rejected": bool(known_guard_rejected),
                    "cursor_before": int(known_cursor_before),
                    "cursor_after": int(known_cursor),
                    "route": route_info,
                },
                "vote": {
                    "candidate_count": len(getattr(policy, "last_candidates", [])),
                    "chosen_by_policy": getattr(policy, "last_choice", {}),
                    "candidates": getattr(policy, "last_candidates", [])[:12],
                },
                "observable_evidence": {
                    "before_hash": before_hash,
                    "after_hash": after_hash,
                    "frame_delta": int(delta),
                    "level_before": int(prev_level),
                    "level_after": int(new_level),
                    "level_delta": int(level_delta),
                    "available_actions": available,
                    "state_after": _state_name(nxt),
                },
                "outcome_tags": outcome_tags,
                "learning_update": learn,
            },
            "learn": learn,
        }
        writer.record_step(spec.game_id, row)
        frame = nxt
        stats["steps"] = step + 1
        stats["best_levels"] = max(stats["best_levels"], new_level)
        stats["won"] = bool(_is_win(frame))
        stats["win_levels"] = int(getattr(frame, "win_levels", stats["win_levels"]) or stats["win_levels"])

        if args.checkpoint_every and (step + 1) % int(args.checkpoint_every) == 0:
            writer.checkpoint(f"{spec.game_id}_step_{step+1}", stats)

        if _is_done(frame):
            break
        if new_level != level:
            level = new_level
            known_cursor = 0
            known_route = archive.route_for(spec.game_id, level) if args.use_known_sequences else None

    return stats


def cmd_train_until_won(args: argparse.Namespace) -> int:
    writer = ArtifactWriter(args.artifacts)
    archive = known_archive(args)
    prefixes = []
    if args.games:
        prefixes = [x.strip() for x in args.games.split(",") if x.strip()]
    specs = select_games(prefixes)
    if not specs:
        print("No games selected", file=sys.stderr)
        return 2
    if args.max_games:
        specs = specs[: int(args.max_games)]

    summary = {
        "mode": "train-until-won",
        "game_count": len(specs),
        "use_known_sequences": bool(args.use_known_sequences),
        "allow_root_alias": bool(args.allow_root_alias),
        "max_steps": int(args.max_steps),
        "max_episodes": int(args.max_episodes) if args.max_episodes else None,
        "results": [],
    }
    writer.status({"status": "running", "completed": 0, "total": len(specs), "current": None})

    episodes_run = 0
    for idx, spec in enumerate(specs, 1):
        if args.max_episodes and episodes_run >= int(args.max_episodes):
            break
        writer.status({"status": "running", "completed": idx - 1, "total": len(specs), "current": spec.game_id})
        try:
            result = run_one_game(spec, args, writer, archive)
        except Exception as e:
            result = {
                "game_id": spec.game_id,
                "root": spec.root,
                "variant": spec.variant,
                "steps": 0,
                "best_levels": 0,
                "won": False,
                "error": repr(e),
                "traceback_tail": traceback.format_exc().splitlines()[-10:],
            }
        episodes_run += 1
        result["episode_index"] = episodes_run
        summary["results"].append(result)
        writer.summary(summary)
        writer.status({"status": "running", "completed": idx, "total": len(specs), "current": spec.game_id, "last": result})
        print(f"[{idx:02d}/{len(specs):02d}] {spec.game_id} won={result.get('won')} levels={result.get('best_levels')}/{result.get('win_levels')} steps={result.get('steps')} err={result.get('error')}")

    won = sum(1 for r in summary["results"] if r.get("won"))
    total_levels = sum(int(r.get("best_levels", 0) or 0) for r in summary["results"])
    summary["completed_episodes"] = episodes_run
    summary["won_games"] = won
    summary["total_levels_completed"] = total_levels
    summary["status"] = "complete"
    writer.summary(summary)
    writer.status({"status": "complete", "completed": episodes_run, "total": len(specs), "won_games": won, "total_levels_completed": total_levels})
    writer.report(render_report(summary))
    return 0


def render_report(summary: dict[str, Any]) -> str:
    lines = ["# ARC-AGI-3 Termux Harness Reasoning Report", "", f"Use known sequences: `{summary.get('use_known_sequences')}`", f"Allow root alias: `{summary.get('allow_root_alias')}`", "", "| Game | Won | Levels | Steps | Error |", "|---|---:|---:|---:|---|"]
    for r in summary.get("results", []):
        levels = f"{r.get('best_levels', 0)}/{r.get('win_levels', 0)}"
        lines.append(f"| {r.get('game_id')} | {r.get('won')} | {levels} | {r.get('steps', 0)} | {str(r.get('error') or '')[:80]} |")
    lines += ["", "## Notes", "", "- This harness is for local public-game training on Termux.", "- Exact known routes are diagnostic. For Kaggle generalization, prefer learned policy outputs and frame-hash-gated memories over blind route replay."]
    return "\n".join(lines) + "\n"


def cmd_summary(args: argparse.Namespace) -> int:
    p = Path(args.artifacts) / "summary.json"
    if not p.exists():
        print(f"Missing {p}", file=sys.stderr)
        return 1
    print(p.read_text(encoding="utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arc3-harness", description="Termux ARC-AGI-3 public 25-game training harness")
    p.add_argument("--offline", action="store_true", help="Accepted for compatibility; harness is local/offline.")
    p.add_argument("--cached-manifest", action="store_true", help="Accepted for compatibility; manifest is packaged.")
    p.add_argument("--use-known-sequences", action="store_true", help="Enable diagnostic known-sequence archive.")
    p.add_argument("--allow-root-alias", action="store_true", help="Allow root-level known sequence aliasing. Risky; disabled by default.")
    p.add_argument("--artifacts", default="artifacts", help="Artifact output directory.")
    p.add_argument("--seed", type=int, default=918)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list-games")
    s.set_defaults(func=cmd_list_games)

    s = sub.add_parser("list-known-sequences")
    s.add_argument("--enabled-only", action="store_true")
    s.set_defaults(func=cmd_list_known_sequences)

    s = sub.add_parser("train-until-won")
    s.add_argument("--games", default="", help="Comma-separated roots/game IDs, e.g. ls20,ar25")
    s.add_argument("--max-games", type=int, default=0)
    s.add_argument("--max-episodes", type=int, default=0)
    s.add_argument("--max-steps", type=int, default=80)
    s.add_argument("--checkpoint-every", type=int, default=0)
    s.set_defaults(func=cmd_train_until_won)

    s = sub.add_parser("summary")
    s.set_defaults(func=cmd_summary)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
