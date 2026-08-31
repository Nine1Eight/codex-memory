#!/usr/bin/env python3
"""Dependency-free repository lint and static-safety checks."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in sorted((*ROOT.glob("src/**/*.py"), *ROOT.glob("tests/**/*.py"))):
    text = path.read_text(encoding="utf-8")
    ast.parse(text, filename=str(path))
    if any(line.rstrip() != line for line in text.splitlines()):
        raise SystemExit(f"trailing whitespace: {path}")
for path in ROOT.glob("src/mock_tools/*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = {"socket", "requests", "urllib", "subprocess"}
    for item in ast.walk(tree):
        if isinstance(item, ast.Import) and any(alias.name.split(".")[0] in forbidden for alias in item.names):
            raise SystemExit(f"forbidden mock-tool import: {path}")
        if isinstance(item, ast.ImportFrom) and (item.module or "").split(".")[0] in forbidden:
            raise SystemExit(f"forbidden mock-tool import: {path}")
print("static checks passed")
