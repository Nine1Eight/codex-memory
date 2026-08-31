#!/usr/bin/env python3
# SIGILAGI v2.2 — REAL GGUF INGESTION + SIGIL PIPELINE

import struct, json, hashlib, zlib
import numpy as np
from pathlib import Path
from PIL import Image

# ============================================================
# UTIL
# ============================================================

def sha256(b): return hashlib.sha256(b).hexdigest()

# ============================================================
# GGUF PARSER (REAL MINIMAL)
# ============================================================

GGUF_MAGIC = b"GGUF"

def read_string(f):
    length = struct.unpack("<Q", f.read(8))[0]
    return f.read(length).decode()

def parse_gguf(path):
    tensors = []

    with open(path, "rb") as f:
        if f.read(4) != GGUF_MAGIC:
            raise RuntimeError("Not GGUF")

        version = struct.unpack("<I", f.read(4))[0]
        tensor_count = struct.unpack("<Q", f.read(8))[0]
        kv_count = struct.unpack("<Q", f.read(8))[0]

        # skip KV metadata
        for _ in range(kv_count):
            _ = read_string(f)
            typ = struct.unpack("<I", f.read(4))[0]
            if typ == 0: f.read(1)
            elif typ == 1: f.read(2)
            elif typ == 2: f.read(4)
            elif typ == 3: f.read(8)
            elif typ == 4:
                l = struct.unpack("<Q", f.read(8))[0]
                f.read(l)
            elif typ == 5:
                n = struct.unpack("<Q", f.read(8))[0]
                for _ in range(n): read_string(f)

        # tensor metadata
        meta = []
        for _ in range(tensor_count):
            name = read_string(f)
            ndim = struct.unpack("<I", f.read(4))[0]
            shape = tuple(struct.unpack("<Q", f.read(8))[0] for _ in range(ndim))
            dtype = struct.unpack("<I", f.read(4))[0]
            offset = struct.unpack("<Q", f.read(8))[0]

            meta.append((name, shape, dtype, offset))

        base = f.tell()

        # read tensors
        for name, shape, dtype, offset in meta:
            f.seek(base + offset)

            size = int(np.prod(shape))

            # assume float32 for now (expand later)
            data = np.fromfile(f, dtype=np.float32, count=size)
            tensors.append((name, data.reshape(shape)))

    return tensors

# ============================================================
# FIELD COMPRESSION
# ============================================================

def decompose(W):
    seed = int(sha256(W.tobytes())[:8], 16) % (2**32)
    rng = np.random.default_rng(seed)

    base = rng.standard_normal(W.shape)
    U = rng.standard_normal((W.shape[0], 8))
    V = rng.standard_normal((8, W.shape[1]))
    approx = base + (U @ V)

    residual = W - approx

    return seed, approx, residual

def quantize(residual):
    scale = np.max(np.abs(residual)) / 127.0 + 1e-8
    q = (residual / scale).astype(np.int8)
    return q, scale

def dequantize(q, scale):
    return q.astype(np.float32) * scale

# ============================================================
# REGEN
# ============================================================

def regenerate(shape, seed, rank, q, scale):
    rng = np.random.default_rng(seed)
    base = rng.standard_normal(shape)
    U = rng.standard_normal((shape[0], rank))
    V = rng.standard_normal((rank, shape[1]))

    approx = base + (U @ V)
    return approx + dequantize(q, scale)

# ============================================================
# BRAILLE
# ============================================================

def encode_braille(data):
    return ''.join(chr(0x2800 + b) for b in data)

def decode_braille(s):
    return np.array([ord(c) - 0x2800 for c in s], dtype=np.uint8)

# ============================================================
# SIGIL PACK
# ============================================================

def pack_tensor(name, shape, seed, q, scale):
    payload = {
        "name": name,
        "shape": shape,
        "seed": seed,
        "rank": 8,
        "scale": scale,
        "q": q.tolist()
    }
    raw = json.dumps(payload).encode()
    comp = zlib.compress(raw, 9)
    glyphs = encode_braille(comp)
    return f"{len(comp)}:{glyphs}"

def unpack_tensor(block):
    size, glyphs = block.split(":", 1)
    comp = decode_braille(glyphs)
    raw = zlib.decompress(comp.tobytes())
    return json.loads(raw)

# ============================================================
# IMAGE
# ============================================================

def sigil_to_image(sigil, path):
    b = sigil.encode()
    side = int(np.ceil(np.sqrt(len(b))))
    img = np.zeros((side, side), dtype=np.uint8)
    img.flat[:len(b)] = np.frombuffer(b, dtype=np.uint8)
    Image.fromarray(img).save(path)

def image_to_sigil(path):
    img = np.array(Image.open(path))
    return bytes(img.flatten()).rstrip(b"\x00").decode()

# ============================================================
# PIPELINE
# ============================================================

def encode_gguf(path):
    tensors = parse_gguf(path)
    blocks = []

    for name, W in tensors[:10]:  # limit for safety
        seed, approx, residual = decompose(W)
        q, scale = quantize(residual)

        block = pack_tensor(name, W.shape, seed, q, scale)
        blocks.append(block)

        print("[ENCODE]", name, W.shape)

    sigil = "GLYPH_SIGIL_v2.2|" + "|".join(blocks)

    sigil_to_image(sigil, "model_sigil.png")
    print("[OK] model_sigil.png written")

def decode_gguf(image):
    sigil = image_to_sigil(image)
    parts = sigil.split("|")[1:]

    tensors = []

    for block in parts:
        p = unpack_tensor(block)
        W = regenerate(
            tuple(p["shape"]),
            p["seed"],
            p["rank"],
            np.array(p["q"], dtype=np.int8),
            p["scale"]
        )
        tensors.append((p["name"], W))
        print("[DECODE]", p["name"], W.shape)

    return tensors

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage:")
        print(" encode <model.gguf>")
        print(" decode <model_sigil.png>")
        exit()

    if sys.argv[1] == "encode":
        encode_gguf(sys.argv[2])
    elif sys.argv[1] == "decode":
        decode_gguf(sys.argv[2])
