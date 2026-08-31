#!/usr/bin/env bash
set -e

PROJECT="sigilagi_minimal_submission"
OUT="$HOME/$PROJECT"
ZIP="$HOME/${PROJECT}.zip"

cd "$HOME/gemma4good-sigilagi"

rm -rf "$OUT" "$ZIP"
mkdir -p "$OUT"

rm -rf __pycache__ app/__pycache__ .pytest_cache
find . -type f -name "*.pyc" -delete

cp -r app docs examples scripts "$OUT/"
cp app.py "$OUT/app.py"
cp README.md "$OUT/README.md"
cp architecture.md "$OUT/architecture.md"
cp demo_script.md "$OUT/demo_script.md"
cp submission_writeup.md "$OUT/submission_writeup.md"
cp KAGGLE_SUBMISSION.md "$OUT/KAGGLE_SUBMISSION.md"
cp requirements.txt "$OUT/requirements.txt"
cp LICENSE "$OUT/LICENSE"

cd "$HOME"

if ! command -v zip >/dev/null 2>&1; then
  pkg install -y zip
fi

zip -r "$ZIP" "$PROJECT" >/dev/null

echo "[OK] Created minimal zip:"
ls -lh "$ZIP"

cp "$ZIP" /sdcard/Download/
echo "[OK] Copied to Downloads:"
ls -lh "/sdcard/Download/${PROJECT}.zip"
