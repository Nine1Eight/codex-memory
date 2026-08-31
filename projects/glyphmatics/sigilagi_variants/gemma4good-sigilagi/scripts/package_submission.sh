#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

PROJECT="gemma4good-sigilagi"
OUT_DIR="$HOME/${PROJECT}_submission"
ZIP_PATH="$HOME/${PROJECT}_submission.zip"

echo "[SigilAGI] Cleaning old package..."
rm -rf "$OUT_DIR" "$ZIP_PATH"

echo "[SigilAGI] Verifying project..."
./scripts/verify_project.sh

echo "[SigilAGI] Copying files..."
mkdir -p "$OUT_DIR"

cp -r \
  app \
  assets \
  docs \
  examples \
  scripts \
  hf_space \
  README.md \
  README_HF_SPACE.md \
  architecture.md \
  demo_script.md \
  submission_writeup.md \
  KAGGLE_SUBMISSION.md \
  FINAL_SUBMISSION_CHECKLIST.md \
  requirements.txt \
  LICENSE \
  .gitignore \
  "$OUT_DIR"

cp app.py "$OUT_DIR/app.py"

echo "[SigilAGI] Removing cache..."
find "$OUT_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$OUT_DIR" -type f -name "*.pyc" -delete

echo "[SigilAGI] Creating zip..."
cd "$HOME"
zip -r "$ZIP_PATH" "${PROJECT}_submission" >/dev/null

echo "[OK] Package created:"
echo "$ZIP_PATH"

echo
echo "[Package contents]"
unzip -l "$ZIP_PATH" | head -120
