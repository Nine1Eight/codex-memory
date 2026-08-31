from pathlib import Path
import ast
import re
import sys

ROOT = Path.cwd()
OUT = ROOT / "looki-cohost-studio.html"

parts = {}
sources = {}

def extract_with_ast(path: Path):
    found = {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return found

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"part1", "part2", "part3", "part4"}:
                    try:
                        value = ast.literal_eval(node.value)
                        if isinstance(value, str):
                            found[target.id] = value
                    except Exception:
                        pass
    return found

def extract_with_regex(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    found = {}

    pattern = re.compile(
        r"(part[1-4])\s*=\s*(?P<quote>'''|\"\"\")(?P<body>.*?)(?P=quote)",
        re.DOTALL
    )

    for m in pattern.finditer(text):
        found[m.group(1)] = m.group("body")

    return found

for py in sorted(ROOT.glob("*.py")):
    if py.name == Path(__file__).name:
        continue

    found = extract_with_ast(py)
    if not found:
        found = extract_with_regex(py)

    for k, v in found.items():
        parts[k] = v
        sources[k] = py.name

missing = [f"part{i}" for i in range(1, 5) if f"part{i}" not in parts]

if missing:
    print("❌ Missing:", ", ".join(missing))
    print()
    print("Scanned Python files:")
    for py in sorted(ROOT.glob("*.py")):
        print(" -", py.name)
    print()
    print("Fix: put part1, part2, part3, and part4 assignments in one .py file, then rerun this.")
    sys.exit(1)

full = parts["part1"] + parts["part2"] + parts["part3"] + parts["part4"]

# Patch: prevent arrow/space page navigation while typing
full = full.replace(
"""document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); nextPage(); }
  if (e.key === 'ArrowLeft') { e.preventDefault(); prevPage(); }
});""",
"""document.addEventListener('keydown', (e) => {
  const tag = (e.target && e.target.tagName) ? e.target.tagName.toUpperCase() : '';
  const typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable;
  if (typing) return;

  if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); nextPage(); }
  if (e.key === 'ArrowLeft') { e.preventDefault(); prevPage(); }
});"""
)

# Patch: add HTML escaping helper before chat rendering
full = full.replace(
"// ===== CHAT =====\nfunction addChat(who, text) {",
"""// ===== CHAT =====
function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, ch => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[ch]));
}

function addChat(who, text) {"""
)

# Patch: escape user chat content only
full = full.replace(
"""div.innerHTML = `<div style="font-size: 10px; color: var(--text-faint); margin-bottom: 3px; display: flex; align-items: center; gap: 4px;"><span style="width: 5px; height: 5px; border-radius: 999px; background: var(--accent); box-shadow: 0 0 6px var(--accent-glow);"></span>You</div>${text}`;""",
"""div.innerHTML = `<div style="font-size: 10px; color: var(--text-faint); margin-bottom: 3px; display: flex; align-items: center; gap: 4px;"><span style="width: 5px; height: 5px; border-radius: 999px; background: var(--accent); box-shadow: 0 0 6px var(--accent-glow);"></span>You</div>${escapeHTML(text)}`;"""
)

OUT.write_text(full, encoding="utf-8")

checks = {
    "DOCTYPE": full.lstrip().startswith("<!DOCTYPE"),
    "Closing HTML": full.rstrip().endswith("</html>"),
    "Page 1": 'id="page1"' in full,
    "Page 2": 'id="page2"' in full,
    "Page 3": 'id="page3"' in full,
    "Page 4": 'id="page4"' in full,
    "Page 5": 'id="page5"' in full,
    "Page 6": 'id="page6"' in full,
    "State Core": "const State" in full,
    "Chat": "function sendChat()" in full,
    "Timer": "session.timer" in full,
    "Export": "downloadPackage" in full,
    "Toast": "function toast(" in full,
    "Keyboard Typing Guard": "const typing =" in full,
    "HTML Escape Guard": "function escapeHTML" in full,
}

print(f"✅ BUILT: {OUT}")
print(f"✅ SIZE: {len(full):,} characters")
print()
print("Sources:")
for k in ["part1", "part2", "part3", "part4"]:
    print(f"  {k}: {sources[k]}")
print()
print("Validation:")
for name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {name}")

if not all(checks.values()):
    raise SystemExit("❌ Build validation failed.")

print()
print("✅ Ready: open looki-cohost-studio.html")
