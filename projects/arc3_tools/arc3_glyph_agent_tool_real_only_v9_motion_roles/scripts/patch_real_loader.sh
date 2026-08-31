#!/usr/bin/env bash
set -euo pipefail

STARTER="${1:-${HOME}/arc3_api_run/ARC-AGI-3-Kaggle-Starter}"
PLAY_LOCAL="$STARTER/scripts/play_local.py"

if [[ ! -f "$PLAY_LOCAL" ]]; then
  echo "Missing real runner: $PLAY_LOCAL" >&2
  exit 1
fi

python3 - "$PLAY_LOCAL" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
s = path.read_text(encoding="utf-8")

changed = False

if "import sys" not in s.splitlines()[:30]:
    # Add sys near the other imports.
    lines = s.splitlines()
    insert_at = 0
    for i, line in enumerate(lines[:40]):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1
    lines.insert(insert_at, "import sys")
    s = "\n".join(lines) + "\n"
    changed = True

old = "module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)"
new = "module = importlib.util.module_from_spec(spec)\n    sys.modules[spec.name] = module\n    spec.loader.exec_module(module)"

if old in s and new not in s:
    s = s.replace(old, new)
    changed = True

old2 = "module = importlib.util.module_from_spec(spec)\n    assert spec.loader is not None\n    spec.loader.exec_module(module)"
new2 = "module = importlib.util.module_from_spec(spec)\n    assert spec.loader is not None\n    sys.modules[spec.name] = module\n    spec.loader.exec_module(module)"

if old2 in s and new2 not in s:
    s = s.replace(old2, new2)
    changed = True

if not changed and "sys.modules[spec.name] = module" not in s:
    print("Could not find expected importlib loader block to patch.", file=sys.stderr)
    print("Search for 'module_from_spec' in scripts/play_local.py and add:", file=sys.stderr)
    print("    sys.modules[spec.name] = module", file=sys.stderr)
    print("before:", file=sys.stderr)
    print("    spec.loader.exec_module(module)", file=sys.stderr)
    sys.exit(1)

path.write_text(s, encoding="utf-8")
print(f"Patched real loader: {path}")
PY
