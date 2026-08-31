#!/usr/bin/env python3
import sys, struct, json, hashlib
from pathlib import Path

GGUF_PATH = Path("Qwen2.gguf")

def sha256_file(path, chunk=1024*1024):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def pack_header(pid, ptype, size):
    return struct.pack(">BBQ", pid, ptype, size)

if not GGUF_PATH.exists():
    sys.exit(f"[ERR] Missing {GGUF_PATH}")

gguf_size = GGUF_PATH.stat().st_size
gguf_hash = sha256_file(GGUF_PATH)

manifest = {
    "sigilagi": "Φ-333",
    "model": "Qwen2",
    "source": "GGUF",
    "original_name": GGUF_PATH.name,
    "bytes": gguf_size,
    "sha256": gguf_hash,
    "canon": "VISIBLE_111",
    "semantic_mapping": "ordinal",
    "payloads": [
        {"id": 0, "type": "weights", "format": "gguf"},
        {"id": 1, "type": "manifest"}
    ]
}

# Payload 0 — GGUF weights (streamed)
sys.stdout.buffer.write(pack_header(0, 0x02, gguf_size))
with GGUF_PATH.open("rb") as f:
    while True:
        chunk = f.read(1024 * 1024)
        if not chunk:
            break
        sys.stdout.buffer.write(chunk)

# Payload 1 — manifest
manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()
sys.stdout.buffer.write(pack_header(1, 0x03, len(manifest_bytes)))
sys.stdout.buffer.write(manifest_bytes)
