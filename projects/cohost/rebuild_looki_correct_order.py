from pathlib import Path

OUT = Path.home() / "cohost" / "looki-cohost-studio.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

required = ["part1", "part2", "part3", "part4"]
missing = [name for name in required if name not in globals()]

if missing:
    raise RuntimeError(
        "Missing variables: "
        + ", ".join(missing)
        + "\nRun this rebuild block after defining part1, part2, part3, and part4."
    )

# Correct assembly order
full = part1 + part2 + part3 + part4

# Safety patch 1: prevent space/arrow navigation while typing
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

# Safety patch 2: add HTML escaping helper before chat rendering
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

# Safety patch 3: escape user-visible user chat text
full = full.replace(
"""div.innerHTML = `<div style="font-size: 10px; color: var(--text-faint); margin-bottom: 3px; display: flex; align-items: center; gap: 4px;"><span style="width: 5px; height: 5px; border-radius: 999px; background: var(--accent); box-shadow: 0 0 6px var(--accent-glow);"></span>You</div>${text}`;""",
"""div.innerHTML = `<div style="font-size: 10px; color: var(--text-faint); margin-bottom: 3px; display: flex; align-items: center; gap: 4px;"><span style="width: 5px; height: 5px; border-radius: 999px; background: var(--accent); box-shadow: 0 0 6px var(--accent-glow);"></span>You</div>${escapeHTML(text)}`;"""
)

OUT.write_text(full, encoding="utf-8")

checks = {
    "DOCTYPE": full.lstrip().startswith("<!DOCTYPE"),
    "Closing HTML": full.rstrip().endswith("</html>"),
    "6 Pages": all(f'id="page{i}"' in full for i in range(1, 7)),
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
print("Validation:")
for name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {name}")

if not all(checks.values()):
    raise SystemExit("❌ Build validation failed.")

print()
print("Ready: open looki-cohost-studio.html in browser.")
