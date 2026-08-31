import numpy as np

class TinyTransformer:
    def __init__(self, vocab=4096, dim=64):
        self.vocab = vocab
        self.dim = dim
        self.emb = np.random.randn(vocab, dim) * 0.02
        self.Wq = np.random.randn(dim, dim) * 0.02
        self.Wk = np.random.randn(dim, dim) * 0.02
        self.Wv = np.random.randn(dim, dim) * 0.02
        self.Wo = np.random.randn(dim, vocab) * 0.02

    def forward(self, seq):
        x = self.emb[seq]

        Q = x @ self.Wq
        K = x @ self.Wk
        V = x @ self.Wv

        attn = Q @ K.T / np.sqrt(self.dim)
        attn = np.exp(attn)
        attn = attn / attn.sum(axis=-1, keepdims=True)

        ctx = attn @ V
        logits = ctx @ self.Wo

        return logits[-1]

    def next_token(self, seq):
        logits = self.forward(seq)
        probs = np.exp(logits - np.max(logits))
        probs /= probs.sum()
        return int(np.random.choice(len(probs), p=probs))
