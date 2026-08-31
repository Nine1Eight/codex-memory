#!/usr/bin/env python3
# SIGILAGI v2.4 — Pure Weight Generator (No Residuals)

import numpy as np
import json, hashlib, zlib

# ============================================================
# UTIL
# ============================================================

def sha256(b): return hashlib.sha256(b).hexdigest()

def seed_from_tensor(W):
    return int(sha256(W.tobytes())[:8], 16)

# ============================================================
# GENERATOR FUNCTION G
# ============================================================

class WeightGenerator:
    def __init__(self, seed, dim, depth=16):
        self.seed = seed
        self.dim = dim
        self.depth = depth

        rng = np.random.default_rng(seed)

        # frequencies + phases
        self.freq = rng.uniform(0.1, 10.0, (depth, 3))
        self.phase = rng.uniform(0, 2*np.pi, depth)

        # projection weights
        self.proj = rng.standard_normal((depth, dim))

    def coord(self, i, j, layer):
        return np.array([i, j, layer], dtype=np.float32)

    def generate(self, shape, layer_id=0):
        H, W = shape
        out = np.zeros((H, W), dtype=np.float32)

        for i in range(H):
            for j in range(W):
                x = self.coord(i, j, layer_id)

                val = 0.0
                for k in range(self.depth):
                    f = self.freq[k]
                    p = self.phase[k]
                    val += np.sin(np.dot(f, x) + p)
                    val += np.cos(np.dot(f, x) - p)

                out[i, j] = val / self.depth

        return out

# ============================================================
# ENCODER (FIND BEST GENERATOR)
# ============================================================

def fit_generator(W):
    best_seed = None
    best_err = float("inf")

    # search seed space (deterministic subset)
    for s in range(32):  # bounded search
        gen = WeightGenerator(s, dim=8)
        approx = gen.generate(W.shape)

        err = np.mean((W - approx)**2)
        if err < best_err:
            best_err = err
            best_seed = s

    return {
        "shape": W.shape,
        "seed": best_seed,
        "depth": 16
    }

# ============================================================
# RECONSTRUCTION
# ============================================================

def rebuild(spec):
    gen = WeightGenerator(spec["seed"], dim=8, depth=spec["depth"])
    return gen.generate(tuple(spec["shape"]))

# ============================================================
# SIGIL PACK
# ============================================================

def pack(specs):
    raw = json.dumps(specs).encode()
    comp = zlib.compress(raw, 9)

    glyphs = ''.join(chr(0x2800 + b) for b in comp)
    return f"GLYPH_SIGIL_v2.4:{len(comp)}:{glyphs}"

def unpack(sigil):
    comp = np.array([ord(c)-0x2800 for c in sigil.split(":",2)[2]], dtype=np.uint8)
    raw = zlib.decompress(comp.tobytes())
    return json.loads(raw)

# ============================================================
# DEMO
# ============================================================

def demo():
    print("=== SIGILAGI v2.4 ===")

    # simulate tensor
    W = np.random.randn(32,32).astype(np.float32)

    spec = fit_generator(W)
    sigil = pack(spec)

    print("Sigil size:", len(sigil))

    decoded = unpack(sigil)
    W2 = rebuild(decoded)

    err = np.mean((W - W2)**2)

    print("Reconstruction MSE:", err)

if __name__ == "__main__":
    demo()
