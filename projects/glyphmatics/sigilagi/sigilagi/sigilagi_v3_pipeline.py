#!/usr/bin/env python3
# SIGILAGI v3 — Full Ingest → Train → Sigil → Rebuild Pipeline

import struct, json, zlib, hashlib
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# ============================================================
# UTIL
# ============================================================

def sha256(b): return hashlib.sha256(b).hexdigest()

# ============================================================
# GGUF INGESTION (REAL)
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

        _ = struct.unpack("<I", f.read(4))[0]
        tensor_count = struct.unpack("<Q", f.read(8))[0]
        kv_count = struct.unpack("<Q", f.read(8))[0]

        # skip KV
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
            meta.append((name, shape, dtype, offset))

        base = f.tell()

        for name, shape, dtype, offset in meta:
            f.seek(base + offset)
            size = int(np.prod(shape))
            data = np.fromfile(f, dtype=np.float32, count=size)
            tensors.append((name, data.reshape(shape)))

    return tensors

# ============================================================
# GENERATOR Gθ
# ============================================================

def fourier(coords, bands=6):
    freqs = 2.0 ** torch.arange(bands, device=coords.device)
    xb = coords.unsqueeze(-1) * freqs
    return torch.cat([torch.sin(xb), torch.cos(xb)], dim=-1).flatten(-2)

class G(nn.Module):
    def __init__(self, latent=64, width=192, depth=6):
        super().__init__()
        self.latent = latent

        in_dim = 3 * 2 * 6
        self.film_g = nn.Linear(latent, in_dim)
        self.film_b = nn.Linear(latent, in_dim)

        layers = []
        d = in_dim
        for _ in range(depth):
            layers += [nn.Linear(d, width), nn.SiLU()]
            d = width
        self.mlp = nn.Sequential(*layers)
        self.out = nn.Linear(width, 1)

    def forward(self, coords, z):
        pe = fourier(coords)

        if z.dim() == 1:
            z = z.unsqueeze(0).expand(pe.size(0), -1)

        x = pe * (1 + self.film_g(z)) + self.film_b(z)
        return self.out(self.mlp(x)).squeeze(-1)

# ============================================================
# DATASET
# ============================================================

def sample_tensor(W, layer, n=4096):
    H, Wd = W.shape[:2]
    i = torch.randint(0, H, (n,))
    j = torch.randint(0, Wd, (n,))
    l = torch.full_like(i, layer)

    coords = torch.stack([l.float(), i.float(), j.float()], dim=-1)
    vals = torch.from_numpy(W[i, j])

    return coords, vals

# ============================================================
# TRAIN
# ============================================================

class Latents(nn.Module):
    def __init__(self, n_models, dim):
        super().__init__()
        self.z = nn.Parameter(torch.randn(n_models, dim) * 0.02)

    def forward(self, idx):
        return self.z[idx]

def train(Gnet, tensors, steps=1000, device="cpu"):
    Gnet.to(device)
    Z = Latents(1, Gnet.latent).to(device)

    opt = torch.optim.Adam(list(Gnet.parameters()) + list(Z.parameters()), lr=2e-3)

    for step in range(steps):
        loss = 0.0
        z = Z(0)

        for layer, (_, W) in enumerate(tensors[:6]):
            W = W.astype(np.float32)
            coords, vals = sample_tensor(W, layer)

            coords, vals = coords.to(device), vals.to(device)
            pred = Gnet(coords, z)

            loss += F.mse_loss(pred, vals)

        opt.zero_grad()
        loss.backward()
        opt.step()

        if step % 100 == 0:
            print(f"[train] {step} loss={loss.item():.6f}")

    return Gnet, Z

# ============================================================
# REBUILD
# ============================================================

@torch.no_grad()
def rebuild(Gnet, z, shape, layer):
    H, Wd = shape
    coords = torch.tensor([[layer,i,j] for i in range(H) for j in range(Wd)], dtype=torch.float32)
    out = Gnet(coords, z).cpu().numpy()
    return out.reshape(H, Wd)

# ============================================================
# SIGIL
# ============================================================

def pack(Gnet, Z):
    payload = {
        "G": {k: v.detach().cpu().numpy().tolist() for k,v in Gnet.state_dict().items()},
        "Z": Z.z.detach().cpu().numpy().tolist()
    }
    raw = json.dumps(payload).encode()
    comp = zlib.compress(raw, 9)
    glyphs = ''.join(chr(0x2800 + b) for b in comp)
    return f"GLYPH_SIGIL_v3:{len(comp)}:{glyphs}"

def unpack(s):
    comp = [ord(c)-0x2800 for c in s.split(":",2)[2]]
    raw = zlib.decompress(bytes(comp))
    payload = json.loads(raw)

    Gnet = G()
    Gnet.load_state_dict({k: torch.tensor(v) for k,v in payload["G"].items()})
    Z = torch.tensor(payload["Z"])

    return Gnet, Z

# ============================================================
# PIPELINE
# ============================================================

def run_encode(model_path):
    tensors = parse_gguf(model_path)
    print("[INGEST] tensors:", len(tensors))

    Gnet = G()
    Gnet, Z = train(Gnet, tensors)

    sigil = pack(Gnet, Z)

    Path("model.sigil.txt").write_text(sigil)
    print("[OK] model.sigil.txt written")

def run_decode(sigil_path):
    sigil = Path(sigil_path).read_text()
    Gnet, Z = unpack(sigil)

    z = Z[0]
    W = rebuild(Gnet, z, (64,64), 0)

    print("[OK] rebuilt tensor:", W.shape)

# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("encode <model.gguf>")
        print("decode <model.sigil.txt>")
        exit()

    if sys.argv[1] == "encode":
        run_encode(sys.argv[2])
    elif sys.argv[1] == "decode":
        run_decode(sys.argv[2])
