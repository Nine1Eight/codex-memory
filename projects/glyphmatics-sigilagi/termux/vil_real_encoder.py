import numpy as np
from pathlib import Path

MODEL_PATH = Path("models/vil-encoder-v1.2.pt")

class VILEncoder:
    def __init__(self):
        import torch

        if not MODEL_PATH.exists():
            raise RuntimeError(f"[VIL] Model not found at {MODEL_PATH}")

        ckpt = torch.load(MODEL_PATH, map_location="cpu")

        if isinstance(ckpt, dict):
            if "vision_encoder" not in ckpt:
                raise RuntimeError(f"[VIL] Invalid checkpoint keys: {list(ckpt.keys())}")

            self.vision = ckpt["vision_encoder"]
            self.temporal = ckpt["temporal_head"]
        else:
            raise RuntimeError("[VIL] Unsupported checkpoint format")

        self.vision.eval()
        self.temporal.eval()
        self.torch = torch

    def encode(self, glyph_ids):
        x = self.torch.tensor(glyph_ids).unsqueeze(0)

        with self.torch.no_grad():
            v = self.vision(x)
            o = self.temporal(v)

        return o.squeeze(0).cpu().numpy()

_vil = None

def get_vil():
    global _vil
    if _vil is None:
        _vil = VILEncoder()
    return _vil
