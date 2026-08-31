from __future__ import annotations

import argparse
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

from agent import run


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("content-type", "text/plain")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", default="Summarize the corpus.")
    args = parser.parse_args()
    print(asyncio.run(run(args.prompt)))


def main() -> None:
    port = os.environ.get("PORT")
    if port:
        server = HTTPServer(("0.0.0.0", int(port)), Handler)
        server.serve_forever()
    else:
        cli()


if __name__ == "__main__":
    main()
