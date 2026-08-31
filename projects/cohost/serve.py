#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HOST, PORT = "127.0.0.1", 8080
print(f"Looki Studio: http://{HOST}:{PORT}")
ThreadingHTTPServer((HOST, PORT), SimpleHTTPRequestHandler).serve_forever()
