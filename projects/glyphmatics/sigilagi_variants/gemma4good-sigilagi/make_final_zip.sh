#!/usr/bin/env bash
set -e

PROJECT="gemma4good-sigilagi"
ROOT="$HOME/$PROJECT"
OUT_DIR="$HOME/${PROJECT}_submission"
ZIP_PATH="$HOME/${PROJECT}_submission.zip"

cd "$ROOT"

echo "[1/5] Cleaning old package..."
rm -rf "$OUT_DIR" "$ZIP_PATH"
mkdir -p "$OUT_DIR"

echo "[2/5] Removing cache..."
rm -rf __pycache__ app/__pycache__ .pytest_cache
find . -type f -name "*.pyc" -delete

echo "[3/5] Checking Python files..."
python -m py_compile app/sigilagi_core.py app/gemma_reasoner.py app/simple_web_app.py

echo "[4/5] Copying project files..."
cp -r app docs examples scripts "$OUT_DIR/"

[ -d assets ] && cp -r assets "$OUT_DIR/assets"
[ -d hf_space ] && cp -r hf_space "$OUT_DIR/hf_space"

for f in \
  README.md \
  README_HF_SPACE.md \
  architecture.md \
  demo_script.md \
  submission_writeup.md \
  KAGGLE_SUBMISSION.md \
  KAGGLE_FORM_ANSWERS.md \
  FINAL_SUBMISSION_CHECKLIST.md \
  VIDEO_RECORDING_CHECKLIST.md \
  requirements.txt \
  app.py \
  LICENSE \
  .gitignore
do
  [ -f "$f" ] && cp "$f" "$OUT_DIR/"
done

echo "[5/5] Creating zip..."
cd "$HOME"

if ! command -v zip >/dev/null 2>&1; then
  pkg install -y zip
fi

zip -r "$ZIP_PATH" "${PROJECT}_submission" >/dev/null

echo "[OK] Created:"
echo "$ZIP_PATH"

ls -lh "$ZIP_PATH"
