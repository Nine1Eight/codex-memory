#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL="wethepeople918/duckwadl-adl-v3-causal-frontier-scored-run"
COMP="arc-prize-2026-arc-agi-3"

echo "[1/4] Push notebook and start the Kaggle run"
kaggle kernels push -p "$HERE" --accelerator NvidiaRtxPro6000

echo "[2/4] Wait for notebook completion"
while true; do
  STATUS="$(kaggle kernels status "$KERNEL" 2>&1 || true)"
  echo "$STATUS"
  if echo "$STATUS" | grep -qiE 'complete|success'; then
    break
  fi
  if echo "$STATUS" | grep -qiE 'error|failed|cancel'; then
    echo "Kernel run failed"
    exit 2
  fi
  sleep 60
done

echo "[3/4] Verify outputs"
FILES="$(kaggle kernels files "$KERNEL" -v 2>&1)"
echo "$FILES"
echo "$FILES" | grep -q 'submission.parquet' || {
  echo "submission.parquet missing"
  exit 3
}
echo "$FILES" | grep -q 'adl_report.json' || {
  echo "adl_report.json missing"
  exit 4
}
echo "$FILES" | grep -q 'duckwadl_output_manifest.json' || {
  echo "duckwadl_output_manifest.json missing"
  exit 5
}

echo "[4/4] Submit the actual kernel output for scoring"
kaggle competitions submit "$COMP" \
  -k "$KERNEL" \
  -f submission.parquet \
  -m "DuckWADL ADL v3 Causal Frontier true scored run" \
  --wait 43200
