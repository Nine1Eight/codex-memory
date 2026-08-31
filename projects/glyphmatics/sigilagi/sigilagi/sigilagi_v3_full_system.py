#!/usr/bin/env python3
# SIGILAGI v3 FULL SYSTEM

import numpy as np
import struct, json, hashlib
import torch
import torch.nn as nn
import torch.nn.functional as F

# ============================================================
# GGUF PARSER
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

        meta = []
        for _ in range(tensor_count):
            name = read_string(f)
            ndim = struct.unpack("<I", f.read(4))[0]
            shape = tuple(struct.unpack("<Q", f.read(8))[0] for _ in range(ndim))
            f.read(4)
            offset = struct.unpack("<Q", f.read(8))[0]
            meta.append((name, shape, offset))

        base = f.tell()

        for name, shape, offset in meta[:20]:  # limit for runtime
            f.seek(base + offset)
            size = int(np.prod(shape))
            data = np.fromfile(f, dtype=np.float32, count=size)
            tensors.append((name, data.reshape(shape)))

    return tensors

# ============================================================
# SIMILARITY
# ============================================================

def cosine(A,B):
    a,b=A.flatten(),B.flatten()
    return np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-8)

# ============================================================
# GENERATOR
# ============================================================

class G(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3+64,128),
            nn.SiLU(),
            nn.Linear(128,128),
            nn.SiLU(),
            nn.Linear(128,1)
        )

    def forward(self, coords, z):
        if z.dim()==1:
            z=z.unsqueeze(0).expand(coords.size(0),-1)
        x=torch.cat([coords,z],dim=-1)
        return self.net(x).squeeze(-1)

# ============================================================
# TRAIN
# ============================================================

def train(Gnet, tensors):
    z = torch.randn(64, requires_grad=True)

    opt = torch.optim.Adam(list(Gnet.parameters())+[z], lr=1e-3)

    for step in range(300):
        loss=0

        for layer,(name,W) in enumerate(tensors[:5]):
            H,Wd=W.shape[:2]
            i=np.random.randint(0,H,1024)
            j=np.random.randint(0,Wd,1024)

            coords=torch.tensor(np.stack([np.full_like(i,layer),i,j],-1),dtype=torch.float32)
            vals=torch.tensor(W[i,j],dtype=torch.float32)

            pred=Gnet(coords,z)
            loss+=F.mse_loss(pred,vals)

        opt.zero_grad()
        loss.backward()
        opt.step()

        if step%50==0:
            print("[train]",step,loss.item())

    return Gnet,z

# ============================================================
# ANALYSIS
# ============================================================

def analyze(models):
    print("\n=== PATTERN SAMENESS ===")

    base=models[0]

    for name,W in base:
        scores=[]
        for m in models[1:]:
            for n2,W2 in m:
                if n2==name:
                    scores.append(cosine(W,W2))

        if scores:
            print(name[:30], np.mean(scores))

# ============================================================
# MAIN
# ============================================================

if __name__=="__main__":
    import sys

    if len(sys.argv)<2:
        print("Usage: model1.gguf model2.gguf ...")
        exit()

    models=[parse_gguf(p) for p in sys.argv[1:]]

    analyze(models)

    print("\n=== TRAIN GENERATOR ===")
    Gnet=G()
    Gnet,z=train(Gnet,models[0])

    print("\n=== DONE ===")
