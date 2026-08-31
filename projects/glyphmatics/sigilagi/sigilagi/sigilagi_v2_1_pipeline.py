#!/usr/bin/env python3
# SIGILAGI v2.1 — Full Pipeline
# GGUF → Field → Sigil → Image → Regen

import numpy as np
import struct, json, hashlib, zlib
from pathlib import Path
from PIL import Image

# ============================================================
# UTIL
# ============================================================

def sha256(b): return hashlib.sha256(b).hexdigest()

def to_bytes(arr):
    return arr.astype(np.float32).tobytes()

def from_bytes(b, shape):
    return np.frombuffer(b, dtype=np.float32).reshape(shape)

# ============================================================
# GGUF PARSER (MINIMAL TENSOR EXTRACTOR)
# ============================================================

def load_fake_tensor(path):
    # placeholder: replace with real gguf parser later
    data = np.fromfile(path, dtype=np.float32)
    size = int(np.sqrt(len(data)))
    return data[:size*size].reshape(size, size)

# ============================================================
# FIELD DECOMPOSITION
# ============================================================

def decompose(W):
    seed = int(sha256(W.tobytes())[:8], 16) % (2**32)
    rng = np.random.default_rng(seed)

    base = rng.standard_normal(W.shape)
    U = rng.standard_normal((W.shape[0], 8))
    V = rng.standard_normal((8, W.shape[1]))
    low_rank = U @ V

    approx = base + low_rank
    residual = W - approx

    return {
        "shape": W.shape,
        "seed": seed,
        "rank": 8,
        "residual": residual
    }

# ============================================================
# QUANTIZE RESIDUAL
# ============================================================

def quantize(residual):
    scale = np.max(np.abs(residual)) / 127.0 + 1e-8
    q = (residual / scale).astype(np.int8)
    return q, scale

def dequantize(q, scale):
    return q.astype(np.float32) * scale

# ============================================================
# REGENERATE
# ============================================================

def regenerate(spec, q, scale):
    rng = np.random.default_rng(spec["seed"])
    base = rng.standard_normal(spec["shape"])
    U = rng.standard_normal((spec["shape"][0], spec["rank"]))
    V = rng.standard_normal((spec["rank"], spec["shape"][1]))
    approx = base + (U @ V)

    residual = dequantize(q, scale)
    return approx + residual

# ============================================================
# BRAILLE ENCODE
# ============================================================

def encode_braille(data):
    return ''.join(chr(0x2800 + b) for b in data)

def decode_braille(s):
    return np.array([ord(c) - 0x2800 for c in s], dtype=np.uint8)

# ============================================================
# SIGIL PACK
# ============================================================

def pack_sigil(spec, q, scale):
    payload = {
        "shape": spec["shape"],
        "seed": spec["seed"],
        "rank": spec["rank"],
        "scale": scale,
        "q": q.tolist()
    }
    raw = json.dumps(payload).encode()
    comp = zlib.compress(raw, 9)
    glyphs = encode_braille(comp)
    return f"GLYPH_SIGIL_v2.1:{len(comp)}:{glyphs}"

def unpack_sigil(s):
    header = s.split(":", 2)
    comp = decode_braille(header[2])
    raw = zlib.decompress(comp.tobytes())
    return json.loads(raw)

# ============================================================
# IMAGE ENCODE
# ============================================================

def sigil_to_image(sigil, out_path):
    data = sigil.encode("utf-8")
    size = int(np.ceil(np.sqrt(len(data))))
    img = np.zeros((size, size), dtype=np.uint8)
    img.flat[:len(data)] = np.frombuffer(data, dtype=np.uint8)
    Image.fromarray(img).save(out_path)

def image_to_sigil(path):
    img = np.array(Image.open(path))
    data = img.flatten()
    return bytes(data).rstrip(b'\x00').decode("utf-8", errors="ignore")

# ============================================================
# PIPELINE
# ============================================================

def encode_pipeline(input_file):
    W = load_fake_tensor(input_file)

    spec = decompose(W)
    q, scale = quantize(spec["residual"])

    sigil = pack_sigil(spec, q, scale)
    sigil_to_image(sigil, "sigil.png")

    print("[OK] Encoded → sigil.png")
    return sigil

def decode_pipeline(image_path):
    sigil = image_to_sigil(image_path)
    payload = unpack_sigil(sigil)

    spec = {
        "shape": tuple(payload["shape"]),
        "seed": payload["seed"],
        "rank": payload["rank"]
    }

    q = np.array(payload["q"], dtype=np.int8)
    scale = payload["scale"]

    W = regenerate(spec, q, scale)
    print("[OK] Reconstructed tensor:", W.shape)
    return W

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage:")
        print("  encode <raw_tensor.bin>")
        print("  decode <sigil.png>")
        exit()

    if sys.argv[1] == "encode":
        encode_pipeline(sys.argv[2])
    elif sys.argv[1] == "decode":
        decode_pipeline(sys.argv[2])
