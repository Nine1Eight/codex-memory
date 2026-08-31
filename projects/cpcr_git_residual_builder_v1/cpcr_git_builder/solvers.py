from __future__ import annotations

import ast
import itertools
import math
import operator
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .normalizers import boxed, normalize_answer

@dataclass
class SolverResult:
    category: str
    answer: str
    verified: bool
    confidence: float
    method: str
    meta: Dict[str, Any]

    def row(self, prompt: str, source: str = "solver") -> dict:
        return {
            "instruction": "Answer the problem. Return only the final boxed answer.",
            "input": prompt,
            "output": boxed(self.answer),
            "prompt": prompt,
            "answer": normalize_answer(self.answer),
            "category": self.category,
            "verified": self.verified,
            "confidence": self.confidence,
            "source": source,
            "method": self.method,
            "meta": self.meta,
        }

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Invert: operator.invert}


def _safe_eval_expr(expr: str) -> Any:
    tree = ast.parse(expr, mode="eval")

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
            left, right = walk(node.left), walk(node.right)
            # Prevent silly huge exponent/shift bombs.
            if isinstance(node.op, (ast.Pow, ast.LShift, ast.RShift)) and abs(right) > 64:
                raise ValueError("unsafe exponent or shift")
            return _ALLOWED_BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
            return _ALLOWED_UNARY[type(node.op)](walk(node.operand))
        raise ValueError(f"unsupported expression node: {type(node).__name__}")

    return walk(tree)


def solve_numeric_expression(prompt: str) -> Optional[SolverResult]:
    pl = prompt.lower()
    # Guard: explicit bitwise language belongs to the bit solver, not numeric.
    if any(tok in pl for tok in ["bitwise", " xor ", "left shift", "right shift", "<<", ">>", "&", "|", " ^ "]):
        return None

    candidates = []
    for pat in [
        r"(?:what is|compute|calculate)\s+([0-9\s+\-*/().%]+)\??",
        r"([0-9]+\s*[+\-*/%]\s*[0-9][0-9\s+\-*/().%]*)",
    ]:
        m = re.search(pat, prompt.lower())
        if m:
            expr = m.group(1).strip().rstrip("? .")
            if re.fullmatch(r"[0-9\s+\-*/().%]+", expr):
                candidates.append(expr)

    for expr in candidates:
        try:
            val = _safe_eval_expr(expr)
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            return SolverResult(
                "equation_numeric",
                str(val),
                True,
                0.95,
                "safe_ast_arithmetic",
                {"expr": expr},
            )
        except Exception:
            continue
    return None

def solve_bit_manipulation(prompt: str) -> Optional[SolverResult]:
    p = prompt.lower()

    # Hard guard: ordinary arithmetic must not leak into bit manipulation.
    bit_signal = any(tok in p for tok in [
        "bitwise",
        " xor ",
        "left shift",
        "right shift",
        "<<",
        ">>",
        "&",
        "|",
        " ^ ",
    ])
    if not bit_signal:
        return None

    expr = None

    # English form: "bitwise xor 13 and 7", "bitwise or 13 with 7".
    mword = re.search(r"(?:bitwise\s+)?(xor|and|or)\s+([0-9]+)\s+(?:and|with)\s+([0-9]+)", p)
    if mword:
        op = {"xor": "^", "and": "&", "or": "|"}[mword.group(1)]
        expr = f"{mword.group(2)} {op} {mword.group(3)}"

    # English shift form.
    if expr is None:
        mshift = re.search(r"(?:left shift|right shift)\s+([0-9]+)\s+(?:by\s+)?([0-9]+)", p)
        if mshift:
            op = "<<" if "left shift" in p else ">>"
            expr = f"{mshift.group(1)} {op} {mshift.group(2)}"

    # Symbolic form: "Compute 6 << 2", "What is 13 ^ 7?"
    if expr is None:
        m = re.search(r"(?:what is|compute|calculate)\s+([0-9\s+\-*/()%^<>&|~]+)", p)
        if m:
            expr = m.group(1).strip().rstrip("? .")

    # Fallback phrase normalization.
    if expr is None:
        q = p.replace("bitwise", "")
        q = q.replace(" xor ", " ^ ").replace(" and ", " & ").replace(" or ", " | ")
        q = q.replace("left shift", "<<").replace("right shift", ">>")
        m2 = re.search(r"([0-9]+\\s*(?:\\^|&|\\||<<|>>)\\s*[0-9]+)", q)
        if m2:
            expr = m2.group(1)

    if not expr or not re.search(r"(<<|>>|[&|^~])", expr):
        return None

    try:
        val = _safe_eval_expr(expr)
        if not isinstance(val, int):
            return None
        return SolverResult(
            "bit_manipulation",
            str(val),
            True,
            0.99,
            "safe_ast_bitwise",
            {"expr": expr},
        )
    except Exception:
        return None

def solve_numeral_system(prompt: str) -> Optional[SolverResult]:
    p = prompt.lower()
    # binary 1010 to decimal
    m = re.search(r"binary\s+([01]+)\s+(?:to|in)\s+decimal", p)
    if m:
        return SolverResult("numeral_system", str(int(m.group(1), 2)), True, 1.0, "binary_to_decimal", {})
    m = re.search(r"hex(?:adecimal)?\s+([0-9a-f]+)\s+(?:to|in)\s+decimal", p)
    if m:
        return SolverResult("numeral_system", str(int(m.group(1), 16)), True, 1.0, "hex_to_decimal", {})
    m = re.search(r"decimal\s+(\d+)\s+(?:to|in)\s+binary", p)
    if m:
        return SolverResult("numeral_system", bin(int(m.group(1)))[2:], True, 1.0, "decimal_to_binary", {})
    m = re.search(r"decimal\s+(\d+)\s+(?:to|in)\s+hex", p)
    if m:
        return SolverResult("numeral_system", hex(int(m.group(1)))[2:].upper(), True, 1.0, "decimal_to_hex", {})
    return None


def solve_unit_conversion(prompt: str) -> Optional[SolverResult]:
    p = prompt.lower().replace("meters", "meter").replace("metres", "meter").replace("kilometers", "kilometer")
    p = p.replace("grams", "gram").replace("minutes", "minute").replace("seconds", "second").replace("hours", "hour")
    rules = [
        (r"([0-9]+(?:\.[0-9]+)?)\s*(?:km|kilometer)\s+(?:to|in)\s*(?:m|meter)", 1000),
        (r"([0-9]+(?:\.[0-9]+)?)\s*(?:m|meter)\s+(?:to|in)\s*(?:cm|centimeter)", 100),
        (r"([0-9]+(?:\.[0-9]+)?)\s*(?:kg|kilogram)\s+(?:to|in)\s*(?:g|gram)", 1000),
        (r"([0-9]+(?:\.[0-9]+)?)\s*hour\s+(?:to|in)\s*minute", 60),
        (r"([0-9]+(?:\.[0-9]+)?)\s*minute\s+(?:to|in)\s*second", 60),
    ]
    for pat, scale in rules:
        m = re.search(pat, p)
        if m:
            val = float(m.group(1)) * scale
            val = int(val) if val.is_integer() else val
            return SolverResult("unit_conversion", normalize_answer(val), True, 1.0, "unit_scale", {"scale": scale})
    return None


def solve_gravity(prompt: str) -> Optional[SolverResult]:
    # Deterministic simple near-earth weight: weight = mass * 9.8
    p = prompt.lower()
    if "gravity" not in p and "weight" not in p:
        return None
    m = re.search(r"mass\s*(?:is|=)?\s*([0-9]+(?:\.[0-9]+)?)\s*kg", p)
    if m and ("earth" in p or "9.8" in p or "weight" in p):
        mass = float(m.group(1))
        val = mass * 9.8
        val = int(val) if val.is_integer() else round(val, 6)
        return SolverResult("physics_gravity", normalize_answer(val), True, 0.98, "weight_mg_earth", {"mass": mass, "g": 9.8})
    return None


def _word_value(word: str, assign: Dict[str, int]) -> int:
    return int("".join(str(assign[ch]) for ch in word))


def solve_cryptarithm(prompt: str, max_permutations: int = 4_000_000) -> Optional[SolverResult]:
    # Supports addition alphametics like SEND + MORE = MONEY and target query "what is MONEY".
    m = re.search(r"\b([A-Z]{1,10})\s*\+\s*([A-Z]{1,10})\s*=\s*([A-Z]{1,12})\b", prompt)
    if not m:
        return None
    a, b, c = m.group(1), m.group(2), m.group(3)
    words = [a, b, c]
    letters = sorted(set("".join(words)))
    if len(letters) > 10:
        return None
    lead = {w[0] for w in words if len(w) > 1}
    target = c
    mt = re.search(r"what\s+is\s+([A-Z]{1,12})", prompt, flags=re.I)
    if mt:
        t = mt.group(1).upper()
        if set(t) <= set(letters):
            target = t

    tried = 0
    for perm in itertools.permutations(range(10), len(letters)):
        tried += 1
        if tried > max_permutations:
            break
        assign = dict(zip(letters, perm))
        if any(assign[ch] == 0 for ch in lead):
            continue
        if _word_value(a, assign) + _word_value(b, assign) == _word_value(c, assign):
            ans = _word_value(target, assign)
            return SolverResult("cryptarithm_deduce", str(ans), True, 0.96, "bruteforce_alphametic_add", {"mapping": assign, "equation": [a, b, c], "target": target, "tried": tried})
    return None


def solve_any(prompt: str) -> Optional[SolverResult]:
    for fn in [solve_unit_conversion, solve_numeral_system, solve_gravity, solve_bit_manipulation, solve_cryptarithm, solve_numeric_expression]:
        res = fn(prompt)
        if res is not None:
            return res
    return None
