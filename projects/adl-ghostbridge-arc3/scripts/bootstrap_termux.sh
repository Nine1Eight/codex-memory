#!/bin/sh
set -eu
(set -o pipefail) >/dev/null 2>&1 && set -o pipefail || true
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
./scripts/verify_environment.sh
PY=""
for candidate in python python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3,10))'; then PY="$candidate"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: supported Python not found" >&2; exit 1; }
if [ ! -x .venv/bin/python ]; then "$PY" -m venv .venv; fi
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
python -c 'import agent, adl, adapters, detectors, ghostbridge, planning, scoring, world'
./scripts/test_all.sh
echo TERMUX_BOOTSTRAP_OK
