#!/usr/bin/env bash
set -euo pipefail

GA_ID="${1:-}"

if [ -z "$GA_ID" ]; then
  echo "Usage: ./add_ga4_to_bench.sh G-XXXXXXXXXX"
  exit 1
fi

python3 <<PY
from pathlib import Path

ga_id = "$GA_ID"
p = Path("index.html")

if not p.exists():
    raise SystemExit("[ERROR] index.html not found. Run this inside the GitHub Pages repo folder.")

s = p.read_text(encoding="utf-8")
backup = p.with_suffix(".html.bak")
backup.write_text(s, encoding="utf-8")

ga_snippet = f'''    <!-- Google Analytics 4 -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{ga_id}');
    </script>
'''

if "googletagmanager.com/gtag/js" not in s:
    s = s.replace("</head>", ga_snippet + "</head>")

track_helper = '''        
        function trackEvent(name, params = {}) {
            if (typeof gtag === 'function') {
                gtag('event', name, params);
            }
        }
'''

if "function trackEvent(name" not in s:
    s = s.replace("        function updateStats() {", track_helper + "\\n        function updateStats() {")

if "bench_start" not in s:
    s = s.replace(
        "            updateStats();\\n        }",
        "            updateStats();\\n            trackEvent('bench_start', { cases: stats.cases });\\n        }",
        1
    )

if "bench_choice" not in s:
    s = s.replace(
        "            // Update stats based on path\\n            updatePathStats(sceneId);",
        "            trackEvent('bench_choice', { scene_id: sceneId });\\n            \\n            // Update stats based on path\\n            updatePathStats(sceneId);"
    )

if "bench_ending" not in s:
    s = s.replace(
        "            stats.cases += 5;\\n            updateStats();",
        "            stats.cases += 5;\\n            updateStats();\\n            trackEvent('bench_ending', { ending_id: endingId, sanity: stats.sanity, authority: stats.authority, guilt: stats.guilt, cases: stats.cases });"
    )

p.write_text(s, encoding="utf-8")
print(f"[OK] Patched {p}")
print(f"[OK] Backup saved as {backup}")
print("[OK] Events tracked: bench_start, bench_choice, bench_ending")
PY
