from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from agents import Agent, Runner, function_tool
from PIL import Image


CORPUS_ROOT = Path(__file__).parent
DEFAULT_SHARD = CORPUS_ROOT / "shards" / "shard_02"


def _load_local_env() -> None:
    env_path = CORPUS_ROOT / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_local_env()


@function_tool
def list_pngs(limit: int = 25, shard: str = "shard_02") -> list[str]:
    """Return a deterministic sample of PNG paths from a shard."""
    shard_dir = CORPUS_ROOT / "shards" / shard
    if not shard_dir.exists():
        shard_dir = DEFAULT_SHARD
    paths = sorted(p for p in shard_dir.glob("*.png"))
    return [str(p) for p in paths[: max(1, min(limit, len(paths))) ]]


@function_tool
def inspect_png(path: str) -> dict:
    """Return lightweight image metadata for a PNG path."""
    p = Path(path)
    with Image.open(p) as im:
        return {
            "path": str(p),
            "size": list(im.size),
            "mode": im.mode,
            "format": im.format,
        }


agent = Agent(
    name="Glyphmatics",
    model="gpt-4.1-mini",
    instructions=(
        "You analyze a corpus of sigil-like PNGs. "
        "When asked about files, inspect representative images, summarize shape patterns, "
        "and keep output concise and factual. "
        "Prefer the provided tools over guessing."
    ),
    tools=[list_pngs, inspect_png],
)


async def run(prompt: str) -> str:
    result = await Runner.run(agent, prompt)
    return result.final_output
