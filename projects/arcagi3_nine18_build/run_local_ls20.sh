#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="${ARC3_REPO_DIR:-$HOME/arc3_api_run/ARC-AGI-3-Agents}"
GAME="${ARC3_GAME:-ls20}"
cd "$REPO_DIR"
export OPERATION_MODE="${OPERATION_MODE:-OFFLINE}"
uv run main.py --agent=nine18worldmodel --game="$GAME"
