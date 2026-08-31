#!/usr/bin/env python3
from __future__ import annotations

import sys
import py_compile
from pathlib import Path

BANNED = [
    "class _Mock",
    "MockAction",
    "mock_play",
    "sample/mock",
    "safe local-test fallback",
    "FrameData:",
    "_MockState",
]

ALLOW_FILES = {
    "scripts/no_mock_audit.py",
    "README.md",
}

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    violations = []

    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.suffix in {".zip", ".pyc"} or "__pycache__" in path.parts:
            continue

        rel = str(path.relative_to(root))
        text = path.read_text(encoding="utf-8", errors="ignore")

        for banned in BANNED:
            if banned in text and rel not in ALLOW_FILES:
                violations.append((rel, banned))

    syntax_errors = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            syntax_errors.append((str(path.relative_to(root)), str(exc)))

    if violations or syntax_errors:
        print("NO-MOCK AUDIT FAILED")
        for rel, banned in violations:
            print(f"  {rel}: contains {banned!r}")
        for rel, err in syntax_errors:
            print(f"  {rel}: syntax/compile error: {err}")
        return 1

    print("NO-MOCK AUDIT OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
