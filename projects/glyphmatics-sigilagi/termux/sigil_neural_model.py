import numpy as np
from pathlib import Path
import json

VOCAB = 4096
DIM = 96
HEADS = 4

def softmax(x):
    x = x - np.max(x)
    e = np.exp(x)
    return e / e.sum()

class NeuralGlyphModel:
    def __init__(self):
        self.emb = np.random.randn(VOCAB, DIM) * 0.02

        self.Wq = np.random.randn(DIM, DIM) * 0.02
        self.Wk = np.random.randn(DIM, DIM) * 0.02
        self.Wv = np.random.randn(DIM, DIM) * 0.02
        self.Wo = np.random.randn(DIM, VOCAB) * 0.02

    def forward(self, seq):
        x = self.emb[seq]  # (T, D)

        Q = x @ self.Wq
        K = x @ self.Wk
        V = x @ self.Wv

        attn = Q @ K.T / np.sqrt(DIM)
        attn = np.exp(attn)
        attn = attn / attn.sum(axis=-1, keepdims=True)

        ctx = attn @ V
        logits = ctx @ self.Wo

        return logits[-1]

    def next_token(self, seq):
        logits = self.forward(seq)
        probs = softmax(logits)
        return int(np.random.choice(len(probs), p=probs))

    def train(self, dataset, epochs=3, lr=0.001):
        for ep in range(epochs):
            total_loss = 0
            for seq in dataset:
                for i in range(1, len(seq)):
                    x = seq[:i]
                    target = seq[i]

                    logits = self.forward(x)
                    probs = softmax(logits)

                    loss = -np.log(probs[target] + 1e-9)
                    total_loss += loss

                    grad = probs
                    grad[target] -= 1

                    # update output layer only (fast + stable)
                    ctx = self.emb[x][-1]
                    self.Wo -= lr * np.outer(ctx, grad)

            print(f"[NEURAL EPOCH {ep+1}] loss={total_loss:.3f}")

    def save(self, path="neural_model.npz"):
        np.savez(path,
            emb=self.emb,
            Wq=self.Wq,
            Wk=self.Wk,
            Wv=self.Wv,
            Wo=self.Wo
        )

    def load(self, path="neural_model.npz"):
        p = Path(path)
        if not p.exists():
            return False
        d = np.load(path)
        self.emb = d["emb"]
        self.Wq = d["Wq"]
        self.Wk = d["Wk"]
        self.Wv = d["Wv"]
        self.Wo = d["Wo"]
        return True
