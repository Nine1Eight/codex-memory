from pathlib import Path

path = Path.home() / "glyphmatics-seo" / "engine" / "generate.py"
text = path.read_text(encoding="utf-8")

text = text.replace(
    "from datetime import datetime",
    "from datetime import datetime, UTC"
)

text = text.replace(
    'now = datetime.utcnow().strftime("%Y-%m-%d")',
    'now = datetime.now(UTC).strftime("%Y-%m-%d")'
)

path.write_text(text, encoding="utf-8")
print("[OK] patched", path)
