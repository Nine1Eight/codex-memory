#!/usr/bin/env python3
# SIGILAGI v3.0 — Neural Weight Generator (Learned G)
# PyTorch implementation

import json, zlib, hashlib
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

# ============================================================
# UTIL
# ============================================================

def sha256(b): return hashlib.sha256(b).hexdigest()

def fourier_features(coords, num_bands=6):
    # coords: (..., 3) for (ℓ, i, j)
    freqs = 2.0 ** torch.arange(num_bands, device=coords.device)
    xb = coords.unsqueeze(-1) * freqs  # (..., 3, B)
    return torch.cat([torch.sin(xb), torch.cos(xb)], dim=-1).flatten(-2)

# ============================================================
# GENERATOR Gθ
# ============================================================

class FiLM(nn.Module):
    def __init__(self, in_dim, cond_dim):
        super().__init__()
        self.gamma = nn.Linear(cond_dim, in_dim)
        self.beta  = nn.Linear(cond_dim, in_dim)

    def forward(self, x, z):
        g = self.gamma(z)
        b = self.beta(z)
        return x * (1 + g) + b

class GeneratorG(nn.Module):
    def __init__(self, latent_dim=64, width=192, depth=6, bands=6):
        super().__init__()
        self.latent_dim = latent_dim
        self.bands = bands

        in_dim = 3 * 2 * bands  # Fourier(ℓ,i,j)
        self.film = FiLM(in_dim, latent_dim)

        layers = []
        d = in_dim
        for _ in range(depth):
            layers += [nn.Linear(d, width), nn.SiLU()]
            d = width
        self.mlp = nn.Sequential(*layers)
        self.out = nn.Linear(width, 1)

    def forward(self, coords, z):
        # coords: (N,3), z: (latent_dim,) or (N, latent_dim)
        pe = fourier_features(coords, self.bands)  # (N, D)
        if z.dim() == 1:
            z = z.unsqueeze(0).expand(pe.size(0), -1)
        x = self.film(pe, z)
        h = self.mlp(x)
        return self.out(h).squeeze(-1)

# ============================================================
# DATASET (tensor → coordinate samples)
# ============================================================

def sample_tensor(W, layer_id, n_samples=4096):
    H, Wd = W.shape
    i = torch.randint(0, H, (n_samples,))
    j = torch.randint(0, Wd, (n_samples,))
    l = torch.full_like(i, layer_id)
    coords = torch.stack([l.float(), i.float(), j.float()], dim=-1)
    vals = W[i, j]
    return coords, vals

# ============================================================
# TRAINING (learn θ and per-model z)
# ============================================================

class LatentBank(nn.Module):
    def __init__(self, n_models, latent_dim):
        super().__init__()
        self.z = nn.Parameter(torch.randn(n_models, latent_dim) * 0.02)

    def forward(self, idx):
        return self.z[idx]

def train_generator(G, tensors_by_model, steps=2000, lr=2e-3, device="cpu"):
    """
    tensors_by_model: list of list of (layer_id, torch.Tensor[H,W])
    """
    G.to(device)
    n_models = len(tensors_by_model)
    Z = LatentBank(n_models, G.latent_dim).to(device)

    opt = torch.optim.Adam(list(G.parameters()) + list(Z.parameters()), lr=lr)

    for step in range(steps):
        m = step % n_models
        z = Z(m)

        loss = 0.0
        for (layer_id, W) in tensors_by_model[m]:
            W = W.to(device)
            coords, vals = sample_tensor(W, layer_id)
            coords, vals = coords.to(device), vals.to(device)
            pred = G(coords, z)
            loss = loss + F.mse_loss(pred, vals)

        opt.zero_grad()
        loss.backward()
        opt.step()

        if (step + 1) % 200 == 0:
            print(f"[train] step={step+1} loss={loss.item():.6f}")

    return G, Z

# ============================================================
# REBUILD FULL TENSOR
# ============================================================

@torch.no_grad()
def rebuild_tensor(G, z, shape, layer_id, device="cpu", batch=8192):
    H, Wd = shape
    coords = []
    for i in range(H):
        for j in range(Wd):
            coords.append([layer_id, i, j])
    coords = torch.tensor(coords, dtype=torch.float32, device=device)

    out = []
    for k in range(0, coords.size(0), batch):
        chunk = coords[k:k+batch]
        pred = G(chunk, z.to(device))
        out.append(pred.cpu())
    flat = torch.cat(out)
    return flat.view(H, Wd)

# ============================================================
# SIGIL PACK (θ + z)
# ============================================================

def state_to_bytes(G, Z):
    payload = {
        "G": {k: v.detach().cpu().numpy().tolist() for k, v in G.state_dict().items()},
        "Z": Z.z.detach().cpu().numpy().tolist()
    }
    raw = json.dumps(payload).encode()
    comp = zlib.compress(raw, 9)
    glyphs = ''.join(chr(0x2800 + b) for b in comp)
    return f"GLYPH_SIGIL_v3.0:{len(comp)}:{glyphs}"

def bytes_to_state(sigil):
    comp = [ord(c) - 0x2800 for c in sigil.split(":", 2)[2]]
    raw = zlib.decompress(bytes(comp))
    payload = json.loads(raw)

    G = GeneratorG()
    sd = {k: torch.tensor(v) for k, v in payload["G"].items()}
    G.load_state_dict(sd)

    Z = torch.tensor(payload["Z"])
    return G, Z

# ============================================================
# DEMO
# ============================================================

def demo():
    print("=== SIGILAGI v3.0 DEMO ===")
    device = "cpu"

    # simulate 2 models × 3 layers
    tensors_by_model = []
    for m in range(2):
        layers = []
        for l in range(3):
            W = torch.randn(64, 64) * (0.5 + 0.5*m)
            layers.append((l, W))
        tensors_by_model.append(layers)

    G = GeneratorG(latent_dim=64, width=192, depth=6)
    G, Z = train_generator(G, tensors_by_model, steps=800, device=device)

    # pack to sigil
    sigil = state_to_bytes(G, Z)
    print("Sigil size:", len(sigil))

    # unpack and rebuild one tensor
    G2, Z2 = bytes_to_state(sigil)
    z0 = Z2[0]
    W_hat = rebuild_tensor(G2, z0, (64,64), layer_id=1)

    print("[OK] Rebuilt tensor shape:", tuple(W_hat.shape))

if __name__ == "__main__":
    demo()
