#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd ~/glyphmatics-seo
python engine/publish.py
echo
echo "[SITE CONTENT]"
ls -l ~/glyphmatics-seo/site/content
