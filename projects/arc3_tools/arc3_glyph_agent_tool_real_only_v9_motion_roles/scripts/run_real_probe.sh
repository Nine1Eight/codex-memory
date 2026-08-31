#!/usr/bin/env bash
set -euo pipefail

STARTER="${1:-${HOME}/arc3_api_run/ARC-AGI-3-Kaggle-Starter}"
GAME="${2:-tr87}"
STEPS="${3:-40}"

if [[ ! -d "$STARTER" ]]; then
  echo "Starter path does not exist: $STARTER" >&2
  exit 1
fi

cd "$STARTER"

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv/bin/python. Run make setup in $STARTER first." >&2
  exit 1
fi

export PYTHONPATH="$PWD:$PWD/vendor/ARC-AGI-3-Agents"
export ARC3_LOG="${ARC3_LOG:-1}"
export ARC3_FRAME_PROBE="${ARC3_FRAME_PROBE:-1}"
export ARC3_FRAME_PROBE_N="${ARC3_FRAME_PROBE_N:-8}"
export ARC3_LOG_DIR="${ARC3_LOG_DIR:-./logs}"

mkdir -p "$ARC3_LOG_DIR"

echo "Running real probe:"
echo "  game=$GAME"
echo "  steps=$STEPS"
echo "  log_dir=$ARC3_LOG_DIR"

.venv/bin/python scripts/play_local.py --game "$GAME" --max-steps "$STEPS"

echo
echo "Probe files:"
ls -lah "$ARC3_LOG_DIR"/frame_probe_* 2>/dev/null || true
