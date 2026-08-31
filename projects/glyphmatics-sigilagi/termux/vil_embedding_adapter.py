#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import numpy as np

from vil_glyph_compiler import compile_base111

DIM = 768
STATE_PATH = "vil_adapter_state.json"

class VILEmbeddingAdapter:
    def __init__(self, dim=DIM):
        self.dim = dim
        self.bias = np.zeros(dim, dtype=np.float32)

    def _index_vec(self, idx, pos):
        seed = f"{idx}:{pos}:vil".encode("utf-8")
        raw = []
        h = hashlib.sha256(seed).digest()
        while len(raw) < self.dim:
            raw.extend(h)
            h = hashlib.sha256(h).digest()
        return np.array(raw[:self.dim], dtype=np.float32) / 255.0

    def encode_ir(self, indices):
        if not indices:
            return np.zeros(self.dim, dtype=np.float32)

        v = np.zeros(self.dim, dtype=np.float32)
        for pos, idx in enumerate(indices):
            token_vec = self._index_vec(idx, pos)
            # temporal weighting
            weight = 1.0 + (pos / max(1, len(indices))) * 0.5
            v += token_vec * weight

        v /= max(1, len(indices))
        v += self.bias

        norm = np.linalg.norm(v)
        if norm > 0:
            v = v / norm

        return v.astype(np.float32)

    def encode_text(self, text):
        return self.encode_ir(compile_base111(text))

    def vector_to_seed(self, text, start=4094, n=12):
        vec = self.encode_text(text)
        out = [start]

        for i in range(n):
            v = float(vec[i % self.dim]) * 255.0
            g = int(abs(v + i * 11)) % 15
            b = int((v * 41 + i * 29)) % 256
            out.append((g << 8) | b)

        return out

    def update(self, text, reward=1.0, lr=0.01):
        vec = self.encode_text(text)
        self.bias = np.clip(self.bias + lr * float(reward) * vec, -1.0, 1.0)

    def save(self, path=STATE_PATH):
        Path(path).write_text(json.dumps({"dim": self.dim, "bias": self.bias.tolist()}))

    def load(self, path=STATE_PATH):
        p = Path(path)
        if not p.exists():
            return False
        d = json.loads(p.read_text())
        self.dim = int(d.get("dim", DIM))
        self.bias = np.array(d.get("bias", [0.0] * self.dim), dtype=np.float32)
        return True

vil_adapter = VILEmbeddingAdapter()
vil_adapter.load()
