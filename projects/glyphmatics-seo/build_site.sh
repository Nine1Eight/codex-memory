#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd ~/glyphmatics-seo
python engine/build_site.py

echo
echo "[SITE ROOT]"
ls -l ~/glyphmatics-seo/site

echo
echo "[ARTICLE DIRS]"
find ~/glyphmatics-seo/site -maxdepth 2 -type f | sort
