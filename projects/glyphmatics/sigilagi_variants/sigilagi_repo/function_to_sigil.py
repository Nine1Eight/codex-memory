#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass
class SigilImage:
    source_name: str
    visible_form: str
    identity_hash: str
    compressed_semantics: Dict[str, Any]
    expansion_map: Dict[str, Any]
    sigil_image: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FunctionToSigil:
    """
    Converts a Python function into a sigil image.

    Model:
        function source
          -> semantic extraction
          -> compression
          -> visible sigil
          -> textual sigil image
    """

    @staticmethod
    def _canonical_json(data: Dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _safe_name(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", name)

    def extract_semantics(self, source: str) -> Dict[str, Any]:
        tree = ast.parse(source)
        fn_nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not fn_nodes:
            raise ValueError("No top-level Python function found in source.")
        if len(fn_nodes) > 1:
            raise ValueError("Provide exactly one top-level function.")

        fn = fn_nodes[0]
        fn_name = fn.name
        arg_names = [a.arg for a in fn.args.args]
        kwonly_names = [a.arg for a in fn.args.kwonlyargs]
        returns = ast.unparse(fn.returns) if fn.returns is not None else None

        calls: List[str] = []
        control_ops: List[str] = []
        assigns: List[str] = []
        literals: List[str] = []
        raises = 0
        returns_count = 0

        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
            elif isinstance(node, ast.If):
                control_ops.append("if")
            elif isinstance(node, ast.For):
                control_ops.append("for")
            elif isinstance(node, ast.While):
                control_ops.append("while")
            elif isinstance(node, ast.Try):
                control_ops.append("try")
            elif isinstance(node, ast.With):
                control_ops.append("with")
            elif isinstance(node, ast.Assign):
                assigns.append("assign")
            elif isinstance(node, ast.AnnAssign):
                assigns.append("ann_assign")
            elif isinstance(node, ast.Constant):
                val = node.value
                if isinstance(val, (str, int, float, bool)) or val is None:
                    literals.append(type(val).__name__)
            elif isinstance(node, ast.Raise):
                raises += 1
            elif isinstance(node, ast.Return):
                returns_count += 1

        doc = ast.get_docstring(fn)
        semantics = {
            "type": "function",
            "language": "python",
            "name": fn_name,
            "arity": len(arg_names) + len(kwonly_names),
            "args": arg_names,
            "kwonly_args": kwonly_names,
            "returns_annotation": returns,
            "is_async": isinstance(fn, ast.AsyncFunctionDef),
            "calls": sorted(set(calls)),
            "control_flow": sorted(set(control_ops)),
            "assignments": len(assigns),
            "literal_types": sorted(set(literals)),
            "raises": raises,
            "return_count": returns_count,
            "has_docstring": doc is not None,
            "doc_summary": (doc.splitlines()[0].strip() if doc else ""),
            "body_statement_count": len(fn.body),
        }
        return semantics

    def compress_semantics(self, semantics: Dict[str, Any]) -> Dict[str, Any]:
        # Minimal, stable semantic compression.
        compressed = {
            "kind": semantics["type"],
            "lang": semantics["language"],
            "name": semantics["name"],
            "shape": {
                "arity": semantics["arity"],
                "async": semantics["is_async"],
                "returns": semantics["returns_annotation"] or "",
                "body_n": semantics["body_statement_count"],
            },
            "ops": {
                "calls": semantics["calls"][:8],
                "flow": semantics["control_flow"][:6],
                "assignments": semantics["assignments"],
                "raises": semantics["raises"],
                "returns": semantics["return_count"],
            },
            "tags": sorted(
                t for t in [
                    "docstring" if semantics["has_docstring"] else "",
                    "pureish" if semantics["raises"] == 0 else "",
                    "control" if semantics["control_flow"] else "",
                    "calls" if semantics["calls"] else "",
                ] if t
            ),
        }
        return compressed

    def render_visible_form(self, compressed: Dict[str, Any]) -> str:
        seed = self._canonical_json(compressed)
        digest = self._sha256(seed)[:12].upper()

        op_map = {
            "if": "◇",
            "for": "↻",
            "while": "⟲",
            "try": "⟁",
            "with": "⟐",
        }

        flow = "".join(op_map.get(x, "•") for x in compressed["ops"]["flow"][:3]) or "·"
        arity = min(int(compressed["shape"]["arity"]), 9)
        call_mark = "λ" if compressed["ops"]["calls"] else "∅"
        async_mark = "⚡" if compressed["shape"]["async"] else "○"

        return f"{async_mark}{call_mark}{flow}{arity}::{digest}"

    def build_sigil_image(self, visible_form: str, compressed: Dict[str, Any]) -> str:
        digest = self._sha256(self._canonical_json(compressed))
        bits = bin(int(digest[:16], 16))[2:].zfill(64)

        # 8x8 deterministic sigil lattice from hash bits
        rows = []
        idx = 0
        for _ in range(8):
            row = []
            for _ in range(8):
                row.append("█" if bits[idx] == "1" else "·")
                idx += 1
            rows.append(" ".join(row))

        header = f"SIGIL {visible_form}"
        border = "═" * max(len(header), 23)

        return "\n".join([
            f"╔{border}╗",
            f"║{header.ljust(len(border))}║",
            f"╠{border}╣",
            *[f"║ {r.ljust(len(border)-1)}║" for r in rows],
            f"╚{border}╝",
        ])

    def convert(self, source: str) -> SigilImage:
        semantics = self.extract_semantics(source)
        compressed = self.compress_semantics(semantics)
        visible = self.render_visible_form(compressed)
        identity = self._sha256(visible + self._canonical_json(compressed))
        sigil_image = self.build_sigil_image(visible, compressed)

        return SigilImage(
            source_name=semantics["name"],
            visible_form=visible,
            identity_hash=identity,
            compressed_semantics=compressed,
            expansion_map={"semantics": semantics},
            sigil_image=sigil_image,
        )


def demo() -> None:
    source = '''
def combine_prices(subtotal: float, discount: float) -> float:
    """Apply a discount to a subtotal."""
    if discount < 0:
        raise ValueError("discount must be non-negative")
    final_total = subtotal - discount
    return round(final_total, 2)
'''.strip()

    converter = FunctionToSigil()
    sigil = converter.convert(source)
    print(json.dumps(sigil.to_dict(), indent=2))
    print()
    print(sigil.sigil_image)


if __name__ == "__main__":
    demo()
