import json
import hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np

DIM = 64
EMB_PATH = "trainable_embedding.json"

def _hash_vec(text):
    h = hashlib.sha256(text.encode("utf-8")).digest()
    raw = list(h)
    while len(raw) < DIM:
        h = hashlib.sha256(h).digest()
        raw.extend(list(h))
    return np.array(raw[:DIM], dtype=np.float32) / 255.0

class TrainableGlyphEmbedding:
    def __init__(self, dim=DIM):
        self.dim = dim
        self.word_vecs = {}
        self.counts = defaultdict(int)

    def encode_text(self, text):
        parts = [x for x in text.lower().split() if x.strip()]
        if not parts:
            parts = list(text)

        vec = np.zeros(self.dim, dtype=np.float32)
        for p in parts:
            if p not in self.word_vecs:
                self.word_vecs[p] = _hash_vec(p).tolist()
            vec += np.array(self.word_vecs[p], dtype=np.float32)

        return vec / max(1, len(parts))

    def encode(self, text):
        return self.encode_text(text)

    def update(self, text, reward=1.0, lr=0.03):
        direction = _hash_vec(text)
        direction = direction / max(1e-9, np.linalg.norm(direction))

        parts = [x for x in text.lower().split() if x.strip()]
        if not parts:
            parts = list(text)

        for p in parts:
            if p not in self.word_vecs:
                self.word_vecs[p] = _hash_vec(p).tolist()

            v = np.array(self.word_vecs[p], dtype=np.float32)
            v = np.clip(v + lr * float(reward) * direction, 0.0, 1.0)
            self.word_vecs[p] = v.tolist()
            self.counts[p] += 1

    def vector_to_seed(self, text, start=4094, n=8):
        vec = self.encode_text(text)
        out = [start]
        for i in range(n):
            v = float(vec[i % self.dim]) * 255.0
            g = int(abs(v + i * 7)) % 15
            b = int((v * 31 + i * 17)) % 256
            out.append((g << 8) | b)
        return out

    def save(self, path=EMB_PATH):
        Path(path).write_text(json.dumps({
            "dim": self.dim,
            "word_vecs": self.word_vecs,
            "counts": dict(self.counts)
        }))

    def load(self, path=EMB_PATH):
        p = Path(path)
        if not p.exists():
            return False
        d = json.loads(p.read_text())
        self.dim = d.get("dim", DIM)
        self.word_vecs = d.get("word_vecs", {})
        self.counts = defaultdict(int, {k:int(v) for k,v in d.get("counts", {}).items()})
        return True

# backward-compatible alias
TrainableEmbedding = TrainableGlyphEmbedding
embedding_model = TrainableGlyphEmbedding()
embedding_model.load()
