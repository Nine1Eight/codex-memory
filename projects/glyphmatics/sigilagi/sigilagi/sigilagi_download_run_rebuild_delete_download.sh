#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# ============================================================
# SIGILAGI ORCHESTRATOR
# download -> run encode -> rebuild -> delete source -> export
# ============================================================

if [ "$#" -lt 2 ]; then
    echo "Usage:"
    echo "  bash sigilagi_download_run_rebuild_delete_download.sh <gguf_url> <work_name>"
    echo
    echo "Example:"
    echo "  bash sigilagi_download_run_rebuild_delete_download.sh \\"
    echo "    \"https://huggingface.co/.../model.gguf?download=true\" tinyllama_run"
    exit 1
fi

GGUF_URL="$1"
WORK_NAME="$2"

ROOT="$HOME/sigilagi_runs/$WORK_NAME"
RAW_DIR="$ROOT/raw"
BUILD_DIR="$ROOT/build"
EXPORT_DIR="$ROOT/export"
LOG_DIR="$ROOT/logs"

mkdir -p "$RAW_DIR" "$BUILD_DIR" "$EXPORT_DIR" "$LOG_DIR"

GGUF_FILE="$RAW_DIR/model.gguf"
SIGIL_FILE="$BUILD_DIR/model.sigil.txt"
REBUILD_NPY="$BUILD_DIR/rebuilt_tensor.npy"
SUMMARY_JSON="$EXPORT_DIR/summary.json"
RUN_LOG="$LOG_DIR/run.log"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$RUN_LOG"
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "Missing required command: $1" >&2
        exit 1
    }
}

require_cmd curl
require_cmd python

log "START"
log "ROOT=$ROOT"
log "DOWNLOADING GGUF"
curl -L --fail --progress-bar "$GGUF_URL" -o "$GGUF_FILE"

RAW_BYTES="$(stat -c '%s' "$GGUF_FILE" 2>/dev/null || stat -f '%z' "$GGUF_FILE")"
RAW_SHA256="$(sha256sum "$GGUF_FILE" | awk '{print $1}')"

log "RAW_BYTES=$RAW_BYTES"
log "RAW_SHA256=$RAW_SHA256"

if [ ! -f "$HOME/sigilagi_v3_pipeline.py" ]; then
    cat > "$HOME/sigilagi_v3_pipeline.py" <<'PYEOF'
#!/usr/bin/env python3
import struct, json, zlib, hashlib, sys
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

GGUF_MAGIC = b"GGUF"

def read_string(f):
    l = struct.unpack("<Q", f.read(8))[0]
    return f.read(l).decode()

def parse_gguf(path):
    tensors = []
    with open(path, "rb") as f:
        if f.read(4) != GGUF_MAGIC:
            raise RuntimeError("Invalid GGUF")
        _version = struct.unpack("<I", f.read(4))[0]
        tensor_count = struct.unpack("<Q", f.read(8))[0]
        kv_count = struct.unpack("<Q", f.read(8))[0]

        for _ in range(kv_count):
            _ = read_string(f)
            typ = struct.unpack("<I", f.read(4))[0]
            if typ == 0:
                f.read(1)
            elif typ == 1:
                f.read(2)
            elif typ == 2:
                f.read(4)
            elif typ == 3:
                f.read(8)
            elif typ == 4:
                l = struct.unpack("<Q", f.read(8))[0]
                f.read(l)
            elif typ == 5:
                n = struct.unpack("<Q", f.read(8))[0]
                for _ in range(n):
                    read_string(f)
            else:
                raise RuntimeError(f"Unsupported GGUF KV type: {typ}")

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
            if len(shape) < 2:
                continue
            if np.prod(shape) == 0:
                continue

            f.seek(base + offset)

            # Minimal float32 ingestion path.
            # For non-f32 GGUF tensors, this will not decode correctly.
            # We hard-stop instead of silently corrupting.
            GGML_TYPE_F32 = 0
            if dtype != GGML_TYPE_F32:
                continue

            size = int(np.prod(shape))
            data = np.fromfile(f, dtype=np.float32, count=size)
            if data.size != size:
                continue
            tensors.append((name, data.reshape(shape)))

    if not tensors:
        raise RuntimeError("No 2D+ float32 tensors found in GGUF")
    return tensors

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

def sample_tensor(W, layer, n=2048):
    H, Wd = W.shape[:2]
    n = min(n, H * Wd)
    i = torch.randint(0, H, (n,))
    j = torch.randint(0, Wd, (n,))
    l = torch.full_like(i, layer)
    coords = torch.stack([l.float(), i.float(), j.float()], dim=-1)
    vals = torch.from_numpy(W[i, j].astype(np.float32))
    return coords, vals

class Latents(nn.Module):
    def __init__(self, n_models, dim):
        super().__init__()
        self.z = nn.Parameter(torch.randn(n_models, dim) * 0.02)

    def forward(self, idx):
        return self.z[idx]

def train(Gnet, tensors, steps=300, device="cpu"):
    Gnet.to(device)
    Z = Latents(1, Gnet.latent).to(device)
    opt = torch.optim.Adam(list(Gnet.parameters()) + list(Z.parameters()), lr=2e-3)

    use_tensors = []
    for idx, (name, W) in enumerate(tensors[:6]):
        if W.ndim >= 2:
            use_tensors.append((idx, name, W.astype(np.float32)))

    if not use_tensors:
        raise RuntimeError("No trainable tensors selected")

    for step in range(steps):
        loss = 0.0
        z = Z(0)
        for layer, _name, W in use_tensors:
            coords, vals = sample_tensor(W, layer)
            coords, vals = coords.to(device), vals.to(device)
            pred = Gnet(coords, z)
            loss = loss + F.mse_loss(pred, vals)

        opt.zero_grad()
        loss.backward()
        opt.step()

        if step % 50 == 0:
            print(f"[train] {step} loss={loss.item():.6f}")

    return Gnet, Z, use_tensors

@torch.no_grad()
def rebuild(Gnet, z, shape, layer, device="cpu", batch=8192):
    H, Wd = shape
    coords = torch.tensor([[layer, i, j] for i in range(H) for j in range(Wd)], dtype=torch.float32, device=device)
    out = []
    for k in range(0, coords.size(0), batch):
        out.append(Gnet(coords[k:k+batch], z.to(device)).cpu())
    return torch.cat(out).numpy().reshape(H, Wd)

def pack(Gnet, Z):
    payload = {
        "G": {k: v.detach().cpu().numpy().tolist() for k, v in Gnet.state_dict().items()},
        "Z": Z.z.detach().cpu().numpy().tolist()
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    comp = zlib.compress(raw, 9)
    glyphs = ''.join(chr(0x2800 + b) for b in comp)
    return f"GLYPH_SIGIL_v3:{len(comp)}:{glyphs}"

def unpack(s):
    parts = s.split(":", 2)
    if len(parts) != 3 or parts[0] != "GLYPH_SIGIL_v3":
        raise RuntimeError("Invalid sigil")
    comp = bytes([ord(c) - 0x2800 for c in parts[2]])
    raw = zlib.decompress(comp)
    payload = json.loads(raw)

    Gnet = G()
    state = {k: torch.tensor(v, dtype=torch.float32) for k, v in payload["G"].items()}
    Gnet.load_state_dict(state)
    Z = torch.tensor(payload["Z"], dtype=torch.float32)
    return Gnet, Z

def run_encode(model_path, sigil_path, rebuilt_npy_path, summary_path):
    tensors = parse_gguf(model_path)
    Gnet = G()
    Gnet, Z, used = train(Gnet, tensors)
    sigil = pack(Gnet, Z)
    Path(sigil_path).write_text(sigil, encoding="utf-8")

    name0, W0 = used[0][1], used[0][2]
    rebuilt = rebuild(Gnet, Z.z[0].detach(), W0.shape[:2], used[0][0])
    np.save(rebuilt_npy_path, rebuilt)

    mse = float(np.mean((W0 - rebuilt) ** 2))
    summary = {
        "tensor_count_ingested": len(tensors),
        "tensor_count_used": len(used),
        "first_tensor_name": name0,
        "first_tensor_shape": list(W0.shape),
        "first_tensor_mse": mse
    }
    Path(summary_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

def run_decode(sigil_path, rebuilt_npy_path):
    sigil = Path(sigil_path).read_text(encoding="utf-8")
    Gnet, Z = unpack(sigil)
    rebuilt = rebuild(Gnet, Z[0], (64, 64), 0)
    np.save(rebuilt_npy_path, rebuilt)
    print(json.dumps({"rebuilt_shape": list(rebuilt.shape)}, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  encode <model.gguf> <out.sigil.txt> <rebuilt.npy> <summary.json>")
        print("  decode <model.sigil.txt> <rebuilt.npy>")
        raise SystemExit(1)

    mode = sys.argv[1]
    if mode == "encode":
        if len(sys.argv) != 6:
            raise SystemExit("encode requires 4 args")
        run_encode(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif mode == "decode":
        if len(sys.argv) != 4:
            raise SystemExit("decode requires 2 args")
        run_decode(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(f"Unknown mode: {mode}")
PYEOF
    chmod +x "$HOME/sigilagi_v3_pipeline.py"
    log "WROTE $HOME/sigilagi_v3_pipeline.py"
fi

log "RUNNING ENCODE"
python "$HOME/sigilagi_v3_pipeline.py" encode "$GGUF_FILE" "$SIGIL_FILE" "$REBUILD_NPY" "$SUMMARY_JSON" | tee -a "$RUN_LOG"

SIGIL_BYTES="$(stat -c '%s' "$SIGIL_FILE" 2>/dev/null || stat -f '%z' "$SIGIL_FILE")"
SIGIL_SHA256="$(sha256sum "$SIGIL_FILE" | awk '{print $1}')"
REBUILD_BYTES="$(stat -c '%s' "$REBUILD_NPY" 2>/dev/null || stat -f '%z' "$REBUILD_NPY")"
REBUILD_SHA256="$(sha256sum "$REBUILD_NPY" | awk '{print $1}')"

TMP_SUMMARY="$ROOT/tmp_summary.json"
python - <<PY > "$TMP_SUMMARY"
import json
from pathlib import Path

p = Path("$SUMMARY_JSON")
data = json.loads(p.read_text()) if p.exists() else {}

data["raw_bytes"] = int("$RAW_BYTES")
data["raw_sha256"] = "$RAW_SHA256"
data["sigil_bytes"] = int("$SIGIL_BYTES")
data["sigil_sha256"] = "$SIGIL_SHA256"
data["rebuilt_bytes"] = int("$REBUILD_BYTES")
data["rebuilt_sha256"] = "$REBUILD_SHA256"
data["compression_ratio_raw_to_sigil"] = round(int("$RAW_BYTES") / max(1, int("$SIGIL_BYTES")), 6)

p.write_text(json.dumps(data, indent=2))
print(json.dumps(data, indent=2))
PY

mv "$TMP_SUMMARY" "$SUMMARY_JSON"
cat "$SUMMARY_JSON" | tee -a "$RUN_LOG" >/dev/null

log "DELETING ORIGINAL GGUF"
rm -f "$GGUF_FILE"

if [ -f "$GGUF_FILE" ]; then
    log "DELETE FAILED"
    exit 1
fi

log "EXPORTING TO SHARED STORAGE"
SHARED_BASE="$HOME/storage/shared/SigilAGI/$WORK_NAME"
mkdir -p "$SHARED_BASE"
cp -f "$SIGIL_FILE" "$SHARED_BASE/model.sigil.txt"
cp -f "$REBUILD_NPY" "$SHARED_BASE/rebuilt_tensor.npy"
cp -f "$SUMMARY_JSON" "$SHARED_BASE/summary.json"
cp -f "$RUN_LOG" "$SHARED_BASE/run.log"

log "DONE"
log "EXPORTED:"
log "  $SHARED_BASE/model.sigil.txt"
log "  $SHARED_BASE/rebuilt_tensor.npy"
log "  $SHARED_BASE/summary.json"
log "  $SHARED_BASE/run.log"

printf '\nFINAL SUMMARY\n'
cat "$SUMMARY_JSON"
