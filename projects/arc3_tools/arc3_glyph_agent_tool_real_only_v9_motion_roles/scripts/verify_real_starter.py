#!/usr/bin/env python3
from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path

def fail(msg: str) -> int:
    print(f"VERIFY FAILED: {msg}", file=sys.stderr)
    return 1

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return fail("Usage: verify_real_starter.py <starter_path> [agent_file]")

    starter = Path(argv[1]).expanduser().resolve()
    agent_file = Path(argv[2]).expanduser().resolve() if len(argv) >= 3 else (starter / "agent" / "my_agent.py")

    if not starter.exists():
        return fail(f"starter path does not exist: {starter}")
    if not agent_file.exists():
        return fail(f"agent file does not exist: {agent_file}")

    sys.path.insert(0, str(starter))

    try:
        arcengine = importlib.import_module("arcengine")
        agents_agent = importlib.import_module("agents.agent")
    except Exception as exc:
        return fail(
            "could not import real starter modules `arcengine` and `agents.agent`. "
            f"Run inside the configured starter environment. Details: {exc}"
        )

    required_arc = ["FrameData", "GameAction", "GameState"]
    for name in required_arc:
        if not hasattr(arcengine, name):
            return fail(f"arcengine missing {name}")

    if not hasattr(agents_agent, "Agent"):
        return fail("agents.agent missing Agent")

    spec = importlib.util.spec_from_file_location("real_my_agent_check", agent_file)
    if spec is None or spec.loader is None:
        return fail(f"could not load agent file: {agent_file}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules["real_my_agent_check"] = mod

    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        return fail(f"agent file failed to import against real starter: {exc}")

    if not hasattr(mod, "MyAgent"):
        return fail("agent file missing MyAgent class")

    cls = mod.MyAgent
    for method in ["is_done", "choose_action"]:
        if not hasattr(cls, method):
            return fail(f"MyAgent missing {method}")
        if not callable(getattr(cls, method)):
            return fail(f"MyAgent.{method} is not callable")

    print("REAL STARTER VERIFY OK")
    print(f"starter: {starter}")
    print(f"agent:   {agent_file}")
    print(f"arcengine: {arcengine.__file__ if hasattr(arcengine, '__file__') else arcengine}")
    print(f"Agent base: {agents_agent.Agent}")
    print(f"MyAgent methods: is_done={inspect.signature(cls.is_done)} choose_action={inspect.signature(cls.choose_action)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
