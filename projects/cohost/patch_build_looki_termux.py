from pathlib import Path

p = Path("build_looki.py")
if not p.exists():
    raise SystemExit("❌ Missing build_looki.py. Save your full pasted code as ~/cohost/build_looki.py first.")

s = p.read_text(encoding="utf-8", errors="ignore")

# Fix Termux path
s = s.replace(
    "/mnt/agents/output/looki-cohost-studio.html",
    "looki-cohost-studio.html"
)

# Fix risky nested f-string validation line
old = """print(f"  6 Pages: {'✅' if all(f'id=\\\\\\"page{i}\\\\\\"' in full for i in range(1,7)) else '❌'}")"""
new = """six_pages_ok = all(('id="page' + str(i) + '"') in full for i in range(1, 7))
print(f"  6 Pages: {'✅' if six_pages_ok else '❌'}")"""

s = s.replace(old, new)

# Also catch the common unescaped variant
old2 = """print(f"  6 Pages: {'✅' if all(f'id="page{i}"' in full for i in range(1,7)) else '❌'}")"""
s = s.replace(old2, new)

p.write_text(s, encoding="utf-8")
print("✅ Patched build_looki.py for Termux")
print("✅ Output will be: ~/cohost/looki-cohost-studio.html")
