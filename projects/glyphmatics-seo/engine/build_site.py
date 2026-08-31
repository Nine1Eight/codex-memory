from pathlib import Path
from html import escape
import re

BASE = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE / "site" / "content"
SITE_DIR = BASE / "site"
SITE_URL = "https://glyphmatics.ai"
BRAND = "GlyphMatics"

def slugify(name: str) -> str:
    return name.lower().replace("_", "-").replace(" ", "-")

def parse_frontmatter_and_body(text: str):
    if not text.startswith("---\n"):
        return {}, text

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text

    fm_raw, body = parts
    fm_lines = fm_raw.splitlines()[1:]
    meta = {}
    current_key = None

    for line in fm_lines:
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z0-9_-]+:\s*", line):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"')
            if value == "":
                meta[key] = []
            else:
                meta[key] = value
            current_key = key
        elif line.strip().startswith("- ") and current_key:
            if not isinstance(meta[current_key], list):
                meta[current_key] = []
            meta[current_key].append(line.strip()[2:].strip().strip('"'))

    return meta, body.strip()

def md_inline(text: str) -> str:
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text

def markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    html = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html.append("</ul>")
            in_list = False

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            close_list()
            i += 1
            continue

        if line.startswith("# "):
            close_list()
            html.append(f"<h1>{md_inline(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            close_list()
            html.append(f"<h2>{md_inline(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            close_list()
            html.append(f"<h3>{md_inline(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            if not in_list:
                html.append("<ul>")
                in_list = True
            html.append(f"<li>{md_inline(line[2:].strip())}</li>")
        else:
            close_list()
            html.append(f"<p>{md_inline(line)}</p>")

        i += 1

    close_list()
    return "\n".join(html)

def article_template(title: str, description: str, canonical: str, body_html: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description)}">
  <link rel="canonical" href="{escape(canonical)}">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{escape(canonical)}">
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #0f1115;
      color: #e8e8e8;
      line-height: 1.6;
    }}
    .wrap {{
      max-width: 900px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }}
    a {{ color: #7cc4ff; }}
    h1, h2, h3 {{ line-height: 1.2; }}
    .top {{
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid #2a2f3a;
    }}
    .brand {{
      font-size: 14px;
      color: #aab4c3;
      margin-bottom: 10px;
    }}
    .card {{
      background: #161a22;
      border: 1px solid #2a2f3a;
      border-radius: 14px;
      padding: 24px;
    }}
    .footer {{
      margin-top: 40px;
      font-size: 14px;
      color: #aab4c3;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div class="brand"><a href="/">GlyphMatics</a></div>
      <div>Deterministic symbolic AI, Visual Instruction Learning, and executable image systems.</div>
    </div>
    <div class="card">
      {body_html}
    </div>
    <div class="footer">
      GlyphMatics — created by Matthew Blake Ward (Nine1Eight).
    </div>
  </div>
</body>
</html>
"""

def index_template(items: list[tuple[str, str, str]]) -> str:
    links = "\n".join(
        f'<li><a href="{href}">{escape(title)}</a><br><small>{escape(desc)}</small></li>'
        for title, href, desc in items
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GlyphMatics | Deterministic Glyph-Based AI</title>
  <meta name="description" content="GlyphMatics articles on deterministic AI, Visual Instruction Learning, executable images, and symbolic computation.">
  <link rel="canonical" href="{SITE_URL}/">
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #0f1115;
      color: #e8e8e8;
      line-height: 1.6;
    }}
    .wrap {{
      max-width: 1000px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }}
    a {{ color: #7cc4ff; }}
    .hero, .card {{
      background: #161a22;
      border: 1px solid #2a2f3a;
      border-radius: 14px;
      padding: 24px;
      margin-bottom: 20px;
    }}
    ul {{
      padding-left: 20px;
    }}
    li {{
      margin-bottom: 16px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>GlyphMatics</h1>
      <p>Deterministic glyph-based computation, Visual Instruction Learning, symbolic AI systems, and executable images.</p>
      <p>Created by Matthew Blake Ward (Nine1Eight).</p>
    </div>
    <div class="card">
      <h2>Articles</h2>
      <ul>
        {links}
      </ul>
    </div>
  </div>
</body>
</html>
"""

def build_articles() -> list[tuple[str, str, str]]:
    items = []

    if not CONTENT_DIR.exists():
        raise FileNotFoundError(f"Missing content directory: {CONTENT_DIR}")

    for md_file in sorted(CONTENT_DIR.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter_and_body(raw)

        title = meta.get("title", md_file.stem.replace("_", " "))
        description = meta.get("description", f"{title} | {BRAND}")
        slug = meta.get("slug", slugify(md_file.stem))
        canonical = meta.get("canonical", f"{SITE_URL}/{slug}/")

        out_dir = SITE_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        body_html = markdown_to_html(body)
        html = article_template(title, description, canonical, body_html)
        (out_dir / "index.html").write_text(html, encoding="utf-8")

        items.append((title, f"/{slug}/", description))

    return items

def build_index(items: list[tuple[str, str, str]]) -> None:
    html = index_template(items)
    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")

def build_robots() -> None:
    robots = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    (SITE_DIR / "robots.txt").write_text(robots, encoding="utf-8")

def build_sitemap(items: list[tuple[str, str, str]]) -> None:
    urls = [f"{SITE_URL}/"] + [f"{SITE_URL}{href}" for _, href, _ in items]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        xml.append("  <url>")
        xml.append(f"    <loc>{escape(url)}</loc>")
        xml.append("  </url>")
    xml.append("</urlset>")
    (SITE_DIR / "sitemap.xml").write_text("\n".join(xml), encoding="utf-8")

def run() -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    items = build_articles()
    build_index(items)
    build_robots()
    build_sitemap(items)
    print("[BUILT] site index, article pages, robots.txt, sitemap.xml")

if __name__ == "__main__":
    run()
