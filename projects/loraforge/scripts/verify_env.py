#!/usr/bin/env python3
from __future__ import annotations

import importlib
import importlib.util
import platform
import sys
from pathlib import Path
from typing import Optional

MODULES = [
    ("torch", "__version__"),
    ("numpy", "__version__"),
    ("transformers", "__version__"),
    ("datasets", "__version__"),
    ("accelerate", "__version__"),
    ("peft", None),
    ("safetensors", None),
    ("huggingface_hub", "__version__"),
    ("sentencepiece", None),
]

SHADOW_NAMES = [m[0] for m in MODULES]


def probe_module(name: str, attr: Optional[str]) -> bool:
    print(f"\n== {name} ==")
    try:
        spec = importlib.util.find_spec(name)
    except Exception as e:
        print(f"FAIL find_spec: {e}")
        return False

    if spec is None:
        print("FAIL not installed")
        return False

    origin = spec.origin
    if origin is None and spec.submodule_search_locations:
        origin = next(iter(spec.submodule_search_locations), None)
    print(f"origin: {origin}")

    try:
        mod = importlib.import_module(name)
    except Exception as e:
        print(f"FAIL import: {e}")
        return False

    if attr and not hasattr(mod, attr):
        print(f"FAIL missing attribute: {attr}")
        return False

    print(f"OK version: {getattr(mod, '__version__', 'unknown')}")
    return True


def main() -> int:
    print("LORAForge environment verification")
    print(f"python: {platform.python_version()} {sys.executable}")
    print(f"platform: {platform.platform()}")
    print(f"cwd: {Path.cwd()}")

    shadows = []
    cwd = Path.cwd()
    for name in SHADOW_NAMES:
        for c in [cwd / f"{name}.py", cwd / name, cwd / f"{name}.pyc"]:
            if c.exists():
                shadows.append(c)
    if (cwd / "__pycache__").exists():
        for name in SHADOW_NAMES:
            shadows.extend((cwd / "__pycache__").glob(f"{name}*.pyc"))

    if shadows:
        print("\nLocal shadow candidates detected:")
        for s in shadows:
            print(f"  - {s}")

    ok = True
    for name, attr in MODULES:
        ok = probe_module(name, attr) and ok

    try:
        import torch
        x = torch.tensor([1, 2, 3]) * 2
        print(f"\ntorch tensor probe: {x.tolist()}")
    except Exception as e:
        print(f"\ntorch tensor probe failed: {e}")
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
