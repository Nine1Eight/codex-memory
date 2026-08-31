#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

PORT="${SIGILAGI_PORT:-7861}"

echo "[SigilAGI] Starting Termux-safe web demo..."
echo "[SigilAGI] No pip install required."
echo "[SigilAGI] Requested URL: http://127.0.0.1:${PORT}"

SIGILAGI_PORT="$PORT" python app/simple_web_app.py
