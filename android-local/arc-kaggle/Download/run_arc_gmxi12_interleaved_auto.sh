#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
OUTDIR="$HOME/storage/downloads/gmxi12_arc_bursttest"
PREFIX="$HOME/storage/downloads/arc_rc9_interleaved"

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
[ -n "$NB" ] && [ -f "$NB" ] || { echo "[FAIL] Could not locate ARC notebook."; exit 1; }

echo "[OK] notebook: $NB"
mkdir -p "$OUTDIR"

echo "[1/5] Building GMXI12 interleaved carrier..."
gmxi12 roundtrip "$NB" \
  --prefix "$PREFIX" \
  --cols 200 \
  --cell 4 \
  --rep 7 \
  --no-svg

echo ""
echo "[2/5] Verify clean pixel carrier..."
gmxi12 verify "$PREFIX.gmxi12.png" --cell 4 --rep 7

echo ""
echo "[3/5] Random redteam to 3%..."
gmxi12 redteam "$NB" \
  --dir "$OUTDIR/random" \
  --cols 200 \
  --cell 4 \
  --rep 7 \
  --rates 0,0.001,0.003,0.005,0.01,0.02,0.03 \
  --trials 5 \
  --no-svg

echo ""
echo "[4/5] Burst/row/column redteam..."
gmxi12 bursttest "$NB" \
  --dir "$OUTDIR/burst" \
  --cols 200 \
  --cell 4 \
  --rep 7 \
  --no-svg

echo ""
echo "[5/5] Final outputs:"
ls -lh "$PREFIX".* "$OUTDIR/random/gmxi12_redteam_report.json" "$OUTDIR/burst/gmxi12_burst_report.json"
