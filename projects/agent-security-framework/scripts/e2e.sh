#!/bin/sh
set -eu
export PYTHONPATH=.
OUT=.test-output
mkdir -p "$OUT"
python -m src.cli validate-scenario fixtures/synthetic_failure.json
python -m src.cli run-scenario fixtures/synthetic_failure.json fixtures/failure_actions.json
python -m src.cli replay fixtures/synthetic_failure.json fixtures/failure_actions.json --runs 3
python -m src.cli minimize fixtures/synthetic_failure.json fixtures/failure_actions.json --output "$OUT/minimized.json"
python -m src.cli evaluate fixtures/synthetic_failure.json fixtures/failure_actions.json
python -m src.cli explore fixtures/synthetic_failure.json --strategy bfs --output "$OUT/explore.json"
python -m src.cli generate-report fixtures/synthetic_failure.json --output "$OUT/report.json"
echo "end-to-end passed"
