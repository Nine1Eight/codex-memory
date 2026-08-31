python3 - <<'PY'
from pathlib import Path
import hashlib
import json

root = Path.home() / "sigilagi_versions" / "v4-core-control-retrieval-pricing-discovery"
files = {}
for p in sorted(root.rglob("*")):
    if p.is_file():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        files[str(p.relative_to(root))] = {"sha256": h, "size": p.stat().st_size}
manifest = {"release": "v4-core-control-retrieval-pricing-discovery", "files": files}
out = root / "RELEASE_MANIFEST.json"
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(out)
PY
