#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple


@dataclass
class SigilImage:
    source_name: str
    language: str
    visible_form: str
    identity_hash: str
    compressed_semantics: Dict[str, Any]
    expansion_map: Dict[str, Any]
    sigil_image: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiLangFunctionToSigil:
    @staticmethod
    def _canonical_json(data: Dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def detect_language(self, source: str) -> str:
        s = source.strip()

        if re.search(r'^\s*(def|async\s+def)\s+\w+\s*\(', s, re.M):
            return "python"
        if re.search(r'function\s+\w+\s*\(', s) or re.search(r'(const|let|var)\s+\w+\s*=\s*\([^)]*\)\s*=>', s):
            return "javascript"
        if re.search(r'^\s*\w+\s*\(\)\s*\{', s, re.M) or re.search(r'^\s*(if|for|while|case)\b', s, re.M):
            return "bash"

        raise ValueError("Unable to detect language. Expected Python, JavaScript, or Bash.")

    def extract_semantics(self, source: str, language: str | None = None) -> Dict[str, Any]:
        lang = language or self.detect_language(source)
        if lang == "python":
            return self._extract_python(source)
        if lang == "javascript":
            return self._extract_javascript(source)
        if lang == "bash":
            return self._extract_bash(source)
        raise ValueError(f"Unsupported language: {lang}")

    def _extract_python(self, source: str) -> Dict[str, Any]:
        tree = ast.parse(source)
        fn_nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not fn_nodes:
            raise ValueError("No top-level Python function found.")
        if len(fn_nodes) > 1:
            raise ValueError("Provide exactly one top-level Python function.")

        fn = fn_nodes[0]
        calls: List[str] = []
        flow: List[str] = []
        assigns = 0
        raises = 0
        returns_count = 0

        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
            elif isinstance(node, ast.If):
                flow.append("if")
            elif isinstance(node, ast.For):
                flow.append("for")
            elif isinstance(node, ast.While):
                flow.append("while")
            elif isinstance(node, ast.Try):
                flow.append("try")
            elif isinstance(node, ast.With):
                flow.append("with")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                assigns += 1
            elif isinstance(node, ast.Raise):
                raises += 1
            elif isinstance(node, ast.Return):
                returns_count += 1

        return {
            "type": "function",
            "language": "python",
            "name": fn.name,
            "arity": len(fn.args.args) + len(fn.args.kwonlyargs),
            "args": [a.arg for a in fn.args.args],
            "calls": sorted(set(calls)),
            "control_flow": sorted(set(flow)),
            "assignments": assigns,
            "raises": raises,
            "return_count": returns_count,
            "is_async": isinstance(fn, ast.AsyncFunctionDef),
            "body_statement_count": len(fn.body),
        }

    def _extract_javascript(self, source: str) -> Dict[str, Any]:
        name = None
        args: List[str] = []

        m = re.search(r'function\s+([A-Za-z_]\w*)\s*\((.*?)\)', source, re.S)
        if m:
            name = m.group(1)
            args = [a.strip() for a in m.group(2).split(",") if a.strip()]
        else:
            m = re.search(r'(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*\((.*?)\)\s*=>', source, re.S)
            if m:
                name = m.group(1)
                args = [a.strip() for a in m.group(2).split(",") if a.strip()]

        if not name:
            raise ValueError("No JavaScript function signature found.")

        calls = re.findall(r'([A-Za-z_]\w*)\s*\(', source)
        calls = [c for c in calls if c not in {"function", name, "if", "for", "while", "switch", "return"}]

        flow = []
        for kw in ("if", "for", "while", "switch", "try"):
            if re.search(rf'\b{kw}\b', source):
                flow.append(kw)

        assigns = len(re.findall(r'(?<![=!<>])=(?!=)', source))
        returns_count = len(re.findall(r'\breturn\b', source))
        throws = len(re.findall(r'\bthrow\b', source))
        is_async = bool(re.search(r'\basync\b', source))

        return {
            "type": "function",
            "language": "javascript",
            "name": name,
            "arity": len(args),
            "args": args,
            "calls": sorted(set(calls)),
            "control_flow": sorted(set(flow)),
            "assignments": assigns,
            "raises": throws,
            "return_count": returns_count,
            "is_async": is_async,
            "body_statement_count": max(1, source.count(";") + source.count("\n")),
        }

    def _extract_bash(self, source: str) -> Dict[str, Any]:
        name = None
        m = re.search(r'^\s*([A-Za-z_]\w*)\s*\(\)\s*\{', source, re.M)
        if m:
            name = m.group(1)
        else:
            name = "script_block"

        flow = []
        for kw in ("if", "for", "while", "case"):
            if re.search(rf'^\s*{kw}\b', source, re.M):
                flow.append(kw)

        calls = []
        for line in source.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if re.match(r'^[A-Za-z_]\w*\(\)\s*\{$', line):
                continue
            first = line.split()[0]
            if first not in {"if", "then", "fi", "for", "do", "done", "while", "case", "esac", "{", "}"}:
                calls.append(first)

        assigns = len(re.findall(r'^\s*[A-Za-z_]\w*=', source, re.M))
        returns_count = len(re.findall(r'^\s*(return|exit)\b', source, re.M))

        return {
            "type": "function",
            "language": "bash",
            "name": name,
            "arity": 0,
            "args": [],
            "calls": sorted(set(calls)),
            "control_flow": sorted(set(flow)),
            "assignments": assigns,
            "raises": 0,
            "return_count": returns_count,
            "is_async": False,
            "body_statement_count": len([ln for ln in source.splitlines() if ln.strip()]),
        }

    def compress_semantics(self, semantics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "kind": semantics["type"],
            "lang": semantics["language"],
            "name": semantics["name"],
            "shape": {
                "arity": semantics["arity"],
                "async": semantics["is_async"],
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
                    "control" if semantics["control_flow"] else "",
                    "calls" if semantics["calls"] else "",
                    "raises" if semantics["raises"] else "",
                    semantics["language"],
                ] if t
            ),
        }

    def render_visible_form(self, compressed: Dict[str, Any]) -> str:
        seed = self._canonical_json(compressed)
        digest = self._sha256(seed)[:12].upper()

        lang_mark = {
            "python": "PY",
            "javascript": "JS",
            "bash": "SH",
        }.get(compressed["lang"], "??")

        op_map = {
            "if": "◇",
            "for": "↻",
            "while": "⟲",
            "try": "⟁",
            "with": "⟐",
            "switch": "⋈",
            "case": "⋔",
        }

        flow = "".join(op_map.get(x, "•") for x in compressed["ops"]["flow"][:3]) or "·"
        arity = min(int(compressed["shape"]["arity"]), 9)
        call_mark = "λ" if compressed["ops"]["calls"] else "∅"
        async_mark = "⚡" if compressed["shape"]["async"] else "○"

        return f"{lang_mark}:{async_mark}{call_mark}{flow}{arity}:{digest}"

    def build_sigil_image(self, visible_form: str, compressed: Dict[str, Any]) -> str:
        digest = self._sha256(self._canonical_json(compressed))
        bits = bin(int(digest[:16], 16))[2:].zfill(64)

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

    def convert(self, source: str, language: str | None = None) -> SigilImage:
        semantics = self.extract_semantics(source, language)
        compressed = self.compress_semantics(semantics)
        visible = self.render_visible_form(compressed)
        identity = self._sha256(visible + self._canonical_json(compressed))
        sigil_image = self.build_sigil_image(visible, compressed)

        return SigilImage(
            source_name=semantics["name"],
            language=semantics["language"],
            visible_form=visible,
            identity_hash=identity,
            compressed_semantics=compressed,
            expansion_map={"semantics": semantics},
            sigil_image=sigil_image,
        )


def demo() -> None:
    examples: List[Tuple[str, str]] = [
        ("python", '''
def combine_prices(subtotal: float, discount: float) -> float:
    if discount < 0:
        raise ValueError("discount must be non-negative")
    final_total = subtotal - discount
    return round(final_total, 2)
'''.strip()),
        ("javascript", '''
function rankHits(hits, topK) {
  if (!hits.length) return [];
  const ranked = hits.sort((a, b) => b.score - a.score);
  return ranked.slice(0, topK);
}
'''.strip()),
        ("bash", '''
rebuild_index() {
  if [ ! -f corpus.json ]; then
    echo "missing corpus" >&2
    exit 1
  fi
  python3 build_index.py
}
'''.strip()),
    ]

    conv = MultiLangFunctionToSigil()
    out = []
    for lang, src in examples:
        sigil = conv.convert(src, lang)
        out.append(sigil.to_dict())

    print(json.dumps(out, indent=2))
    print()
    for item in out:
        print(item["sigil_image"])
        print()


if __name__ == "__main__":
    demo()
