#!/usr/bin/env bash
set -euo pipefail

STARTER="${1:-${HOME}/arc3_api_run/ARC-AGI-3-Kaggle-Starter}"
AGENT="$STARTER/agent/my_agent.py"

if [[ ! -f "$AGENT" ]]; then
  echo "Missing installed agent: $AGENT" >&2
  exit 1
fi

python3 - "$AGENT" <<'PY'
from pathlib import Path
import py_compile
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

s2 = s.replace(
    '"preview": ["".join(str(int(v) % 10 for v in row[:80]) for row in grid[:12]],',
    '"preview": ["".join(str(int(v) % 10) for v in row[:80]) for row in grid[:12]],'
)

if s2 == s:
    print("No matching preview typo found; checking compile anyway.")
else:
    p.write_text(s2, encoding="utf-8")
    print(f"Patched preview syntax typo in {p}")

py_compile.compile(str(p), doraise=True)
print("Installed agent compiles OK")
PY
