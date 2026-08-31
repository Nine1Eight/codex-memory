#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

echo "[ROOT FILES]"
ls -l ~/glyphmatics-seo/site

echo
echo "[INDEX]"
test -f ~/glyphmatics-seo/site/index.html && echo "[OK] index.html"

echo
echo "[ROBOTS]"
test -f ~/glyphmatics-seo/site/robots.txt && echo "[OK] robots.txt"

echo
echo "[SITEMAP]"
test -f ~/glyphmatics-seo/site/sitemap.xml && echo "[OK] sitemap.xml"

echo
echo "[ARTICLE PAGES]"
find ~/glyphmatics-seo/site -mindepth 2 -maxdepth 2 -name index.html | sort
