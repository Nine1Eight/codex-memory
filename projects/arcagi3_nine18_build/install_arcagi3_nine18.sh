#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${ARC3_REPO_DIR:-$HOME/arc3_api_run/ARC-AGI-3-Agents}"
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_SRC="$KIT_DIR/agents_nine18_world_model_agent.py"
AGENT_DST="$REPO_DIR/agents/nine18_world_model_agent.py"

mkdir -p "$(dirname "$REPO_DIR")"

if ! command -v git >/dev/null 2>&1; then
  echo "git is required. Install git, then rerun this script." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install Python 3.10+, then rerun this script." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --user --upgrade uv
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ ! -d "$REPO_DIR/.git" ]; then
  git clone https://github.com/arcprize/ARC-AGI-3-Agents.git "$REPO_DIR"
fi

cd "$REPO_DIR"

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

mkdir -p agents
cp "$AGENT_SRC" "$AGENT_DST"

python3 - <<'PY'
from pathlib import Path

p = Path("agents/__init__.py")
text = p.read_text(encoding="utf-8")
import_line = "from .nine18_world_model_agent import Nine18WorldModel"
if import_line not in text:
    marker = "from .templates.random_agent import Random"
    if marker in text:
        text = text.replace(marker, marker + "\n" + import_line)
    else:
        text = import_line + "\n" + text
if '"Nine18WorldModel"' not in text:
    anchor = '"Random",'
    if anchor in text:
        text = text.replace(anchor, anchor + '\n    "Nine18WorldModel",')
    elif "__all__ = [" in text:
        text = text.replace("__all__ = [", "__all__ = [\n    \"Nine18WorldModel\",")
    else:
        text += '\n__all__ = ["Nine18WorldModel", "AVAILABLE_AGENTS"]\n'
p.write_text(text, encoding="utf-8")
PY

uv sync

echo "Nine18WorldModel installed into: $REPO_DIR"
echo "Run local smoke test with:"
echo "  cd $REPO_DIR && uv run main.py --agent=nine18worldmodel --game=ls20"
echo "Set platform key without printing it:"
echo "  cd $REPO_DIR && ../arcagi3_nine18_build/configure_arc_key.sh"
