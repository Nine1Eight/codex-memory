#!/usr/bin/env python3
# SIGILAGI v3 — Cross-Model Pattern Analyzer

import numpy as np
import struct
from pathlib import Path

# ============================================================
# GGUF PARSER (reuse)
# ============================================================

GGUF_MAGIC = b"GGUF"

def read_string(f):
    l = struct.unpack("<Q", f.read(8))[0]
    return f.read(l).decode()

def parse_gguf(path):
    tensors = []

    with open(path, "rb") as f:
        if f.read(4) != GGUF_MAGIC:
            raise RuntimeError("Invalid GGUF")

        f.read(4)
        tensor_count = struct.unpack("<Q", f.read(8))[0]
        kv_count = struct.unpack("<Q", f.read(8))[0]

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

        meta = []
        for _ in range(tensor_count):
            name = read_string(f)
            ndim = struct.unpack("<I", f.read(4))[0]
            shape = tuple(struct.unpack("<Q", f.read(8))[0] for _ in range(ndim))
            dtype = struct.unpack("<I", f.read(4))[0]
            offset = struct.unpack("<Q", f.read(8))[0]
            meta.append((name, shape, offset))

        base = f.tell()

        for name, shape, offset in meta:
            f.seek(base + offset)
            size = int(np.prod(shape))
            data = np.fromfile(f, dtype=np.float32, count=size)
            tensors.append((name, data.reshape(shape)))

    return tensors

# ============================================================
# SIMILARITY METRICS
# ============================================================

def cosine(A, B):
    a = A.flatten()
    b = B.flatten()
    return np.dot(a,b) / (np.linalg.norm(a)*np.linalg.norm(b)+1e-8)

def rank_similarity(A, B, k=8):
    Ua, _, _ = np.linalg.svd(A, full_matrices=False)
    Ub, _, _ = np.linalg.svd(B, full_matrices=False)
    return np.linalg.norm(Ua[:,:k].T @ Ub[:,:k])

def distribution(A, B):
    pa = np.histogram(A, bins=64, density=True)[0] + 1e-8
    pb = np.histogram(B, bins=64, density=True)[0] + 1e-8
    return np.sum(pa * np.log(pa / pb))

def similarity(A, B):
    sc = cosine(A,B)
    sr = rank_similarity(A,B)
    sd = distribution(A,B)

    return 0.5*sc + 0.4*sr - 0.1*sd

# ============================================================
# ANALYSIS
# ============================================================

def analyze(models):
    base = models[0]

    print("=== CROSS MODEL PATTERN ANALYSIS ===\n")

    for i, (name, W) in enumerate(base[:10]):
        scores = []

        for m in models[1:]:
            for n2, W2 in m:
                if n2 == name:
                    s = similarity(W, W2)
                    scores.append(s)

        if scores:
            avg = np.mean(scores)

            if avg > 0.9:
                tag = "IDENTICAL"
            elif avg > 0.7:
                tag = "HIGH SIMILARITY"
            elif avg > 0.5:
                tag = "PARTIAL"
            else:
                tag = "DIVERGENT"

            print(f"{name:40}  {avg:.3f}  {tag}")

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage:")
        print(" analyze model1.gguf model2.gguf ...")
        exit()

    models = []
    for p in sys.argv[1:]:
        print("[LOAD]", p)
        models.append(parse_gguf(p))

    analyze(models)
