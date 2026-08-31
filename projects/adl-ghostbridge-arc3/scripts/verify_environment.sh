#!/bin/sh
set -eu
PY=""
for candidate in python python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3,10))'; then PY="$candidate"; break; fi
done
if [ -z "$PY" ]; then echo "ERROR: Python >=3.10 not found" >&2; exit 1; fi
command -v git >/dev/null 2>&1 || { echo "ERROR: git not found" >&2; exit 1; }
echo "PYTHON=$($PY -c 'import sys; print(sys.executable)')"
echo "VERSION=$($PY -c 'import platform; print(platform.python_version())')"
if [ -n "${TERMUX_VERSION:-}" ] || [ -d /data/data/com.termux/files/usr ]; then echo TERMUX_DETECTED; else echo TERMUX_NOT_DETECTED; fi
