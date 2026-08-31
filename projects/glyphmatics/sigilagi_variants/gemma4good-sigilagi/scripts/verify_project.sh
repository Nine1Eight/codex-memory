#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "[1/6] Removing Python cache..."
rm -rf __pycache__ app/__pycache__ .pytest_cache

echo "[2/6] Checking Python files..."
python -m py_compile \
  app/sigilagi_core.py \
  app/gemma_reasoner.py \
  app/simple_web_app.py

echo "[3/6] Testing core engine..."
python app/sigilagi_core.py \
  --labels "person, phone, door, wallet, paper" \
  --note "Verification test" >/tmp/sigilagi_core_test.json

grep -q "☉ → ☏ → ⛩ → ▨ → ▧" /tmp/sigilagi_core_test.json

echo "[4/6] Testing reasoning layer..."
python app/gemma_reasoner.py \
  --labels "person, phone, door, wallet, paper" \
  --note "Verification reasoning test" >/tmp/sigilagi_reasoning_test.json

grep -q "organized symbolic reasoning trace" /tmp/sigilagi_reasoning_test.json

echo "[5/6] Checking removed names..."
if grep -Rni "looki\|relief" . \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude="*.pyc"; then
  echo "[FAIL] old project references found"
  exit 1
else
  echo "[OK] no old references found"
fi

echo "[6/6] Listing project files..."
find . -maxdepth 3 -type f \
  ! -path "./.git/*" \
  ! -name "*.pyc" \
  | sort

echo
echo "[PASS] SigilAGI project verified."
