#!/usr/bin/env bash
set -euo pipefail

STARTER="${1:-${HOME}/arc3_api_run/ARC-AGI-3-Agents}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash "$HERE/scripts/install_into_starter.sh" "$STARTER"

cd "$STARTER"

if [[ ! -f Makefile ]]; then
  echo "No Makefile found in starter: $STARTER" >&2
  exit 1
fi

export ARC3_LOG="${ARC3_LOG:-1}"
export ARC3_LOG_DIR="${ARC3_LOG_DIR:-./logs}"

echo "Running real ARC local runner in:"
echo "  $STARTER"
echo "Logging:"
echo "  ARC3_LOG=$ARC3_LOG"
echo "  ARC3_LOG_DIR=$ARC3_LOG_DIR"

make play-local
