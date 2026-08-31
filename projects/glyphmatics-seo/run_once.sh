#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd ~/glyphmatics-seo
python engine/generate.py
python engine/optimize.py
python engine/validate.py
python engine/publish.py
python engine/build_site.py

echo
echo "[DONE] one full cycle completed"
