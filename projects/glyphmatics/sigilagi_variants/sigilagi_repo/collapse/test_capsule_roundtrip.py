#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    builder = script_dir / "build_capsule.py"
    fixture_src = script_dir / "fixture_src"
    fixture_out = script_dir / "fixture_capsule.py"

    if fixture_out.exists():
        fixture_out.unlink()

    build = run([
        sys.executable, str(builder),
        "--source-dir", str(fixture_src),
        "--module", "discount_combiner.py",
        "--module", "enhancement_discovery.py",
        "--module", "proxy_pointer_rag.py",
        "--module", "system_refiner.py",
        "--module", "sigil_stack.py",
        "--entry-module", "sigil_stack.py",
        "--entry-class", "SigilAGIStack",
        "--entry-method", "demo",
        "--output", str(fixture_out),
        "--metadata-json", '{"fixture": true, "name": "roundtrip"}'
    ])
    print(build.stdout, end="")
    if build.returncode != 0:
        print(build.stderr, file=sys.stderr, end="")
        return build.returncode

    with tempfile.TemporaryDirectory(prefix="sigil_capsule_test_") as tmp:
        tmp_path = Path(tmp)
        verify = run([sys.executable, str(fixture_out), "--verify-only"], cwd=tmp_path)
        print(verify.stdout, end="")
        if verify.returncode != 0:
            print(verify.stderr, file=sys.stderr, end="")
            return verify.returncode

        full = run([sys.executable, str(fixture_out), "--out", str(tmp_path / "rehydrated")], cwd=tmp_path)
        print(full.stdout, end="")
        if full.returncode != 0:
            print(full.stderr, file=sys.stderr, end="")
            return full.returncode

        expected = {
            "discount_combiner.py",
            "enhancement_discovery.py",
            "proxy_pointer_rag.py",
            "system_refiner.py",
            "sigil_stack.py",
        }
        actual = {p.name for p in (tmp_path / "rehydrated").glob("*.py")}
        if expected != actual:
            print(json.dumps({
                "error": "rehydrated file set mismatch",
                "expected": sorted(expected),
                "actual": sorted(actual),
            }, indent=2))
            return 3

    print(json.dumps({"roundtrip": "ok"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
