#!/usr/bin/env bash
set -euo pipefail

STARTER="${1:-${HOME}/arc3_api_run/ARC-AGI-3-Agents}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "$STARTER" ]]; then
  echo "Starter path does not exist: $STARTER" >&2
  exit 1
fi

if [[ ! -d "$STARTER/agent" ]]; then
  echo "Starter path has no agent/ directory: $STARTER" >&2
  exit 1
fi

if [[ ! -f "$HERE/agent/my_agent.py" ]]; then
  echo "Missing package agent file: $HERE/agent/my_agent.py" >&2
  exit 1
fi

BACKUP="$STARTER/agent/my_agent.py.bak.$(date +%Y%m%d_%H%M%S)"
if [[ -f "$STARTER/agent/my_agent.py" ]]; then
  cp "$STARTER/agent/my_agent.py" "$BACKUP"
  echo "Backed up existing agent to: $BACKUP"
fi

cp "$HERE/agent/my_agent.py" "$STARTER/agent/my_agent.py"

echo "Installed real-only Glyph Flood agent:"
echo "  $STARTER/agent/my_agent.py"
