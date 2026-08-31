#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
OUTDIR="$HOME/storage/downloads/gmxi11_arc_redteam"
PREFIX="$HOME/storage/downloads/arc_rc9_hardened"

TARGETS=(
  "$HOME/rc9_image_safe/output/arc-agi-3-hybrid-solver-bfs-cnn-heuristics_80304e95fc98_20260503_235346.recovered.ipynb"
  "$HOME/storage/downloads/arc-agi-3-hybrid-solver-bfs-cnn-heuristics_80304e95fc98.decoded.ipynb"
  "/storage/emulated/0/Download/arc-agi-3-hybrid-solver-bfs-cnn-heuristics_80304e95fc98.decoded.ipynb"
)

NB=""
for p in "${TARGETS[@]}"; do
  if [ -f "$p" ]; then NB="$p"; break; fi
done

if [ -z "$NB" ]; then
  NB="$(find "$HOME" "$HOME/storage/downloads" /storage/emulated/0/Download /sdcard/Download \
    -maxdepth 8 -type f \
    \( -name '*80304e95fc98*.ipynb' -o -name '*recovered*.ipynb' -o -name '*decoded*.ipynb' \) \
    2>/dev/null | while read -r f; do printf '%s\t%s\n' "$(stat -c %Y "$f" 2>/dev/null || echo 0)" "$f"; done | sort -nr | head -n 1 | cut -f2-)"
fi

if [ -z "$NB" ] || [ ! -f "$NB" ]; then
  echo "[FAIL] Could not locate ARC notebook."
  echo "Run: find \$HOME /storage/emulated/0/Download /sdcard/Download -name '*.ipynb' 2>/dev/null"
  exit 1
fi

echo "[OK] notebook: $NB"

echo "[1/5] Hardened roundtrip..."
gmxi11 roundtrip "$NB" \
  --prefix "$PREFIX" \
  --cols 200 \
  --cell 4 \
  --rep 5 \
  --no-svg

echo ""
echo "[2/5] Verify clean PNG..."
gmxi11 verify "$PREFIX.gmxi11.png" --cell 4 --rep 5

echo ""
echo "[3/5] Damage carrier at 1% random cells..."
gmxi11 damage "$PREFIX.gmxi11.png" \
  --out "$PREFIX.damaged_1pct.png" \
  --rate 0.01 \
  --cell 4 \
  --seed 918

echo ""
echo "[4/5] Recover from damaged PNG..."
gmxi11 unpack "$PREFIX.damaged_1pct.png" \
  --out "$PREFIX.from_damaged_1pct.ipynb" \
  --cell 4 \
  --rep 5

echo ""
echo "[5/5] Hash compare..."
sha256sum "$NB" "$PREFIX.from_pixels.ipynb" "$PREFIX.from_damaged_1pct.ipynb"

echo ""
echo "[OPTIONAL] Running full redteam matrix..."
mkdir -p "$OUTDIR"
gmxi11 redteam "$NB" \
  --dir "$OUTDIR" \
  --cols 200 \
  --cell 4 \
  --rep 5 \
  --rates 0,0.001,0.003,0.005,0.01,0.02 \
  --trials 3 \
  --no-svg

echo ""
echo "[DONE] Hardened outputs:"
ls -lh "$PREFIX".* "$OUTDIR/gmxi11_redteam_report.json"
