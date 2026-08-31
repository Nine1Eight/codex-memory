#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SOURCE_DIR="$HOME/sigilagi_real"
OUT_CAPSULE="$HOME/sigilagi_real_capsule.py"
REHYDRATED_DIR="$HOME/sigilagi_real_out"
LOG_DIR="$HOME/collapse/logs"
BUILD_SCRIPT="$HOME/collapse/build_capsule.py"
ASSERT_SCRIPT="$HOME/collapse/test_expected_output.py"
COMPARE_SCRIPT="$HOME/collapse/compare_rehydrated_hashes.py"

mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/pipeline_${STAMP}.log"

exec > >(tee "$LOG_FILE") 2>&1

echo "[1] direct source execution"
cd "$SOURCE_DIR"
python3 sigil_stack.py

echo
echo "[2] build capsule"
MODULE_ARGS=(
  --module proxy_pointer_rag.py
  --module system_refiner.py
  --module discount_combiner.py
  --module sigil_stack.py
)

if [ -f "$SOURCE_DIR/enhancement_discovery.py" ]; then
  MODULE_ARGS+=(--module enhancement_discovery.py)
  VERSION="v4"
  SLICE="core-control-retrieval-pricing-discovery"
else
  VERSION="v3"
  SLICE="core-control-retrieval-pricing"
fi

python3 "$BUILD_SCRIPT" \
  --source-dir "$SOURCE_DIR" \
  "${MODULE_ARGS[@]}" \
  --entry-module sigil_stack.py \
  --entry-class SigilAGIStack \
  --entry-method demo \
  --output "$OUT_CAPSULE" \
  --metadata-json "{\"name\":\"sigilagi-real\",\"version\":\"${VERSION}\",\"slice\":\"${SLICE}\"}"

echo
echo "[3] verify capsule"
python3 "$OUT_CAPSULE" --verify-only

echo
echo "[4] rehydrate + boot"
rm -rf "$REHYDRATED_DIR"
python3 "$OUT_CAPSULE" --out "$REHYDRATED_DIR"

echo
echo "[5] assert expected output"
python3 "$ASSERT_SCRIPT" --source "$SOURCE_DIR" --rehydrated "$REHYDRATED_DIR"

echo
echo "[6] compare hashes"
python3 "$COMPARE_SCRIPT" --source "$SOURCE_DIR" --rehydrated "$REHYDRATED_DIR"

echo
echo "[OK] pipeline complete"
echo "[LOG] $LOG_FILE"
