#!/usr/bin/env python3
# SIGILAGI v2.3 — Cross-Model Compression + Rebuilder

import numpy as np
import json, zlib, hashlib
from pathlib import Path

# ============================================================
# UTIL
# ============================================================

def sha256(b): return hashlib.sha256(b).hexdigest()

# ============================================================
# GLOBAL DICTIONARY (Φ)
# ============================================================

class PatternDictionary:
    def __init__(self, max_patterns=64):
        self.patterns = []
        self.max_patterns = max_patterns

    def add_pattern(self, P):
        if len(self.patterns) < self.max_patterns:
            self.patterns.append(P)
        else:
            # replace lowest-energy pattern
            energies = [np.sum(p**2) for p in self.patterns]
            idx = np.argmin(energies)
            self.patterns[idx] = P

    def match(self, W):
        best_idx = 0
        best_err = float("inf")

        for i, P in enumerate(self.patterns):
            err = np.mean((W - P)**2)
            if err < best_err:
                best_err = err
                best_idx = i

        return best_idx, best_err

Φ = PatternDictionary()

# ============================================================
# PATTERN EXTRACTION
# ============================================================

def extract_pattern(W, rank=8):
    U, S, Vt = np.linalg.svd(W, full_matrices=False)
    return (U[:, :rank] @ np.diag(S[:rank]) @ Vt[:rank, :]).astype(np.float32)

# ============================================================
# MODEL ENCODE
# ============================================================

def encode_tensor(name, W):
    P = extract_pattern(W)
    Φ.add_pattern(P)

    idx, _ = Φ.match(W)
    base = Φ.patterns[idx]

    residual = W - base

    scale = np.max(np.abs(residual)) / 127.0 + 1e-8
    q = (residual / scale).astype(np.int8)

    return {
        "name": name,
        "shape": W.shape,
        "pattern_idx": idx,
        "scale": scale,
        "q": q.tolist()
    }

# ============================================================
# MODEL DECODE
# ============================================================

def decode_tensor(packet):
    P = Φ.patterns[packet["pattern_idx"]]
    q = np.array(packet["q"], dtype=np.int8)
    residual = q.astype(np.float32) * packet["scale"]

    return P + residual

# ============================================================
# SIGIL PACK (MULTI MODEL)
# ============================================================

def pack_models(models):
    payload = {
        "patterns": [p.tolist() for p in Φ.patterns],
        "models": models
    }

    raw = json.dumps(payload).encode()
    comp = zlib.compress(raw, 9)

    glyphs = ''.join(chr(0x2800 + b) for b in comp)
    return f"GLYPH_SIGIL_v2.3:{len(comp)}:{glyphs}"

def unpack_models(sigil):
    parts = sigil.split(":", 2)
    comp = np.array([ord(c)-0x2800 for c in parts[2]], dtype=np.uint8)
    raw = zlib.decompress(comp.tobytes())

    payload = json.loads(raw)

    Φ.patterns = [np.array(p, dtype=np.float32) for p in payload["patterns"]]
    return payload["models"]

# ============================================================
# DEMO (SIMULATED MULTI-MODEL)
# ============================================================

def demo():
    print("=== SIGILAGI v2.3 DEMO ===")

    models = []

    for m in range(3):  # simulate 3 models
        tensors = []
        for i in range(5):
            W = np.random.randn(64,64).astype(np.float32)
            encoded = encode_tensor(f"m{m}_t{i}", W)
            tensors.append(encoded)
        models.append(tensors)

    sigil = pack_models(models)
    print("Sigil size:", len(sigil))

    decoded_models = unpack_models(sigil)

    for model in decoded_models:
        for t in model:
            W = decode_tensor(t)

    print("[OK] Cross-model reconstruction complete")

if __name__ == "__main__":
    demo()
