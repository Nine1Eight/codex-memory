#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(root: Path) -> Dict[str, Dict[str, Any]]:
    files: Dict[str, Dict[str, Any]] = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        files[rel] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare source tree hashes against rehydrated tree hashes")
    parser.add_argument("--source", required=True, help="Original source directory")
    parser.add_argument("--rehydrated", required=True, help="Rehydrated output directory")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    rehydrated = Path(args.rehydrated).expanduser().resolve()

    src = collect(source)
    out = collect(rehydrated)

    result = {
        "source_count": len(src),
        "rehydrated_count": len(out),
        "matching": True,
        "missing_in_rehydrated": sorted(set(src) - set(out)),
        "extra_in_rehydrated": sorted(set(out) - set(src)),
        "mismatches": {},
    }

    common = sorted(set(src) & set(out))
    for rel in common:
        if src[rel] != out[rel]:
            result["matching"] = False
            result["mismatches"][rel] = {
                "source": src[rel],
                "rehydrated": out[rel],
            }

    if result["missing_in_rehydrated"] or result["extra_in_rehydrated"] or result["mismatches"]:
        result["matching"] = False

    print(json.dumps(result, indent=2))
    return 0 if result["matching"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
