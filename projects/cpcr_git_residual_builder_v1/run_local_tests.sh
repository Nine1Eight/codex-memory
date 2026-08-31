#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python - <<'PY'
import torch
import safetensors
print('[OK] torch', torch.__version__)
print('[OK] safetensors', safetensors.__version__)
PY
python -m pytest -q
python -m cpcr_git_builder.cli generate-seed-corpus --out-jsonl build/seed_train.jsonl --report build/seed_report.json
python -m cpcr_git_builder.cli write-test-adapter --adapter-dir build/test_adapter --rank 8 --hidden 64
python -m cpcr_git_builder.cli package-adapter --adapter-dir build/test_adapter --out-zip build/submission.zip
python -m cpcr_git_builder.cli validate-submission --zip build/submission.zip
printf '\n[OK] CPCR-GIT local Linux torch+safetensors test pipeline complete.\n'
