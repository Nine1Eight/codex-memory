from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arcengine import ARCBaseGame, ActionInput, GameAction


@dataclass(frozen=True)
class GameSpec:
    root: str
    variant: str
    game_id: str
    module_path: Path
    metadata_path: Path
    tags: tuple[str, ...]
    baseline_actions: tuple[int, ...]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def environment_root() -> Path:
    return project_root() / "environment_files"


def load_manifest() -> list[GameSpec]:
    specs: list[GameSpec] = []
    env_root = environment_root()
    for meta in sorted(env_root.glob("*/*/metadata.json")):
        data = json.loads(meta.read_text(encoding="utf-8"))
        root = meta.parts[-3]
        variant = meta.parts[-2]
        specs.append(
            GameSpec(
                root=root,
                variant=variant,
                game_id=str(data.get("game_id", f"{root}-{variant}")),
                module_path=meta.parent / f"{root}.py",
                metadata_path=meta,
                tags=tuple(data.get("tags", [])),
                baseline_actions=tuple(int(x) for x in data.get("baseline_actions", [])),
            )
        )
    return specs


def select_games(prefixes: list[str] | None = None) -> list[GameSpec]:
    specs = load_manifest()
    if not prefixes:
        return specs
    out: list[GameSpec] = []
    for spec in specs:
        if any(spec.game_id.startswith(p) or spec.root == p for p in prefixes):
            out.append(spec)
    return out


def load_game_class(spec: GameSpec) -> type[ARCBaseGame]:
    module_name = f"arc3_public_{spec.root}_{spec.variant}"
    if module_name in sys.modules:
        mod = sys.modules[module_name]
    else:
        import os
        old_cwd = Path.cwd()
        try:
            os.chdir(spec.module_path.parent)
            module_spec = importlib.util.spec_from_file_location(module_name, spec.module_path)
            if module_spec is None or module_spec.loader is None:
                raise ImportError(f"Could not load module spec for {spec.module_path}")
            mod = importlib.util.module_from_spec(module_spec)
            sys.modules[module_name] = mod
            module_spec.loader.exec_module(mod)
        finally:
            os.chdir(old_cwd)
    classes = []
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        try:
            if issubclass(obj, ARCBaseGame) and obj is not ARCBaseGame:
                classes.append(obj)
        except Exception:
            pass
    if not classes:
        raise RuntimeError(f"No ARCBaseGame subclass found in {spec.module_path}")
    classes.sort(key=lambda c: c.__name__)
    return classes[-1]


def make_game(spec: GameSpec) -> ARCBaseGame:
    cls = load_game_class(spec)
    return cls()


def action_input(action_id: int, game_id: str, data: dict[str, Any] | None = None, reasoning: dict[str, Any] | None = None) -> ActionInput:
    action = GameAction.from_id(int(action_id))
    payload = dict(data or {})
    payload.setdefault("game_id", game_id)
    if action_id == 6:
        payload.setdefault("x", 0)
        payload.setdefault("y", 0)
    return ActionInput(id=action, data=payload, reasoning=reasoning or {})


def reset_game(game: ARCBaseGame, game_id: str):
    return game.perform_action(action_input(0, game_id, reasoning={"source": "reset"}), raw=True)


def step_game(game: ARCBaseGame, game_id: str, action_id: int, data: dict[str, Any] | None = None, reason: str = ""):
    return game.perform_action(action_input(action_id, game_id, data=data, reasoning={"source": reason[:80]}), raw=True)
