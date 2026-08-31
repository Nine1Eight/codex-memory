#!/bin/sh
set -eu
PY="${PYTHON:-python}"
"$PY" -m scoring.rhae --self-test
"$PY" -m unittest discover -s tests -v
"$PY" -m agent.runtime --dry-run
