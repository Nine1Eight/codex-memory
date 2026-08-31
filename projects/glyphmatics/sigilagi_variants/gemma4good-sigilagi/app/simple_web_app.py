#!/usr/bin/env python3
"""
SigilAGI Termux-Safe Web Demo

No Gradio.
No external Python dependencies.
Uses Python standard library only.
"""

import html
import os
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from sigilagi_core import generate_report


HOST = "0.0.0.0"
PORT = int(os.environ.get("SIGILAGI_PORT", "7861"))


def render_page(labels="", note="", report=None):
    labels_safe = html.escape(labels or "")
    note_safe = html.escape(note or "")

    glyph_summary = ""
    plain_summary = ""
    json_report = ""

    if report:
        glyph_summary = html.escape(report.get("glyph_summary", ""))
        plain_summary = html.escape(report.get("plain_english_summary", ""))
        json_report = html.escape(json.dumps(report, ensure_ascii=False, indent=2))

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>SigilAGI Object-to-Glyph Detection</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      font-family: system-ui, sans-serif;
      background: #0b0f14;
      color: #e8eef6;
      margin: 0;
      padding: 24px;
    }}
    main {{
      max-width: 1000px;
      margin: auto;
    }}
    h1 {{
      font-size: 2rem;
      margin-bottom: 0.25rem;
    }}
    .tagline {{
      color: #aab7c4;
      margin-bottom: 24px;
    }}
    .card {{
      background: #111821;
      border: 1px solid #263241;
      border-radius: 16px;
      padding: 18px;
      margin-bottom: 18px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }}
    label {{
      display: block;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    textarea {{
      width: 100%;
      min-height: 90px;
      border-radius: 12px;
      border: 1px solid #344255;
      background: #090d12;
      color: #e8eef6;
      padding: 12px;
      font-size: 1rem;
      box-sizing: border-box;
    }}
    button {{
      background: #e8eef6;
      color: #0b0f14;
      border: 0;
      border-radius: 12px;
      padding: 12px 16px;
      font-weight: 800;
      cursor: pointer;
      margin-top: 12px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #090d12;
      border: 1px solid #263241;
      border-radius: 12px;
      padding: 14px;
      overflow-x: auto;
    }}
    .glyph {{
      font-size: 1.75rem;
      letter-spacing: 0.1rem;
    }}
    .muted {{
      color: #aab7c4;
    }}
  </style>
</head>
<body>
<main>
  <h1>SigilAGI 🧬</h1>
  <div class="tagline">Object-to-glyph detection for symbolic AI reasoning.</div>

  <section class="card">
    <form method="POST">
      <label>Detected object labels</label>
      <textarea name="labels" placeholder="person, phone, door, wallet">{labels_safe}</textarea>

      <br><br>

      <label>Optional scene note</label>
      <textarea name="note" placeholder="Describe the scene context if needed.">{note_safe}</textarea>

      <button type="submit">Generate SigilAGI Report</button>
    </form>
  </section>

  <section class="card">
    <h2>Glyph Summary</h2>
    <pre class="glyph">{glyph_summary}</pre>
  </section>

  <section class="card">
    <h2>Plain-English Summary</h2>
    <pre>{plain_summary}</pre>
  </section>

  <section class="card">
    <h2>Structured JSON Report</h2>
    <pre>{json_report}</pre>
  </section>

  <section class="card muted">
    <h2>Safety Boundary</h2>
    <p>SigilAGI does not prove identity, intent, guilt, danger, legal status, or medical status.</p>
    <p>It organizes detected objects into a symbolic reasoning trace for human review.</p>
  </section>
</main>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        labels = "person, phone, door, wallet, paper"
        note = "Termux-safe SigilAGI demo"
        report = generate_report(labels, note)
        self.send_html(render_page(labels, note, report))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        data = parse_qs(body)

        labels = data.get("labels", [""])[0]
        note = data.get("note", [""])[0]

        if labels.strip():
            report = generate_report(labels, note)
        else:
            report = {
                "error": "Enter at least one object label.",
                "example": "person, phone, door"
            }

        self.send_html(render_page(labels, note, report))

    def send_html(self, content):
        payload = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print("[SigilAGI]", fmt % args)


def main():
    for port in range(PORT, PORT + 20):
        try:
            server = ThreadingHTTPServer((HOST, port), Handler)
            print(f"[SigilAGI] running at http://127.0.0.1:{port}")
            print("[SigilAGI] press CTRL+C to stop")
            server.serve_forever()
            return
        except OSError as exc:
            if getattr(exc, "errno", None) == 98:
                print(f"[SigilAGI] port {port} busy, trying {port + 1}...")
                continue
            raise

    raise SystemExit("[SigilAGI] no open port found in scan range")


if __name__ == "__main__":
    main()
