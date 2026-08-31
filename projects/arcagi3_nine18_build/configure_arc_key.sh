#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${ARC3_REPO_DIR:-$HOME/arc3_api_run/ARC-AGI-3-Agents}"
cd "$REPO_DIR"
read -rsp "ARC_AGI platform key: " ARC_KEY
echo
export ARC_KEY
python3 - <<'PY'
import os
from pathlib import Path

key = os.environ.get("ARC_KEY", "")
if not key:
    raise SystemExit("No key received.")
path = Path(".env")
existing = path.read_text(encoding="utf-8") if path.exists() else ""
lines = []
written = False
for line in existing.splitlines():
    if line.startswith("ARC_API_KEY="):
        lines.append("ARC_API_KEY=" + key)
        written = True
    else:
        lines.append(line)
if not written:
    lines.append("ARC_API_KEY=" + key)
path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
PY
echo "ARC_API_KEY saved to $REPO_DIR/.env"
