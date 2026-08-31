#!/usr/bin/env python3
import itertools
import re
from typing import Dict, List, Tuple, Optional

def parse_expr(expr: str):
    expr = expr.replace(" ", "").upper()
    if "=" not in expr:
        raise ValueError("Expression must contain '='")
    left, right = expr.split("=")
    addends = left.split("+")
    result = right
    words = addends + [result]
    letters = sorted(set("".join(words)))
    if len(letters) > 10:
        raise ValueError("Too many unique letters for base-10 cryptarithm")
    leading = {w[0] for w in words if len(w) > 1}
    return addends, result, letters, leading

def word_value(word: str, mapping: Dict[str, int]) -> int:
    return int("".join(str(mapping[c]) for c in word))

def solve_cryptarithm(expr: str, max_solutions: int = 1):
    addends, result, letters, leading = parse_expr(expr)

    # Brute-force is acceptable for oracle generation on small puzzles.
    # For production, cache by sorted letters + equation signature.
    digits = range(10)
    sols = []

    for perm in itertools.permutations(digits, len(letters)):
        m = dict(zip(letters, perm))
        if any(m[x] == 0 for x in leading):
            continue

        lhs = sum(word_value(w, m) for w in addends)
        rhs = word_value(result, m)
        if lhs == rhs:
            sols.append(m)
            if len(sols) >= max_solutions:
                break

    return sols

def column_trace(expr: str, mapping: Dict[str, int]) -> Tuple[str, str]:
    addends, result, letters, leading = parse_expr(expr)

    max_len = max(max(len(w) for w in addends), len(result))
    carry = 0
    cols = []

    for i in range(max_len):
        parts = []
        s = carry

        for w in addends:
            ch = w[-1 - i] if i < len(w) else None
            if ch is not None:
                parts.append(ch)
                s += mapping[ch]

        out_ch = result[-1 - i] if i < len(result) else None
        out_digit = s % 10
        next_carry = s // 10

        if out_ch is not None:
            lhs = "+".join(parts + ([f"c{i}" ] if carry else []))
            cols.append(f"C{i}:{lhs}={out_ch}|c{i+1}={next_carry}")
        else:
            cols.append(f"C{i}:carry={next_carry}")

        carry = next_carry

    # If final carry maps to leading result digit, this is already captured by top column.
    ordered_map = ",".join(f"{k}{mapping[k]}" for k in sorted(mapping))
    lhs_val = "+".join(str(word_value(w, mapping)) for w in addends)
    rhs_val = str(word_value(result, mapping))

    trace = "|".join(cols)
    answer = f"{lhs_val}={rhs_val}"
    return trace, f"MAP:{ordered_map}|A:{answer}"

def solve_dual(expr0: str, expr1: str) -> str:
    out = []
    for idx, expr in enumerate([expr0, expr1]):
        sols = solve_cryptarithm(expr, max_solutions=1)
        if not sols:
            out.append(f"P{idx}:{expr}|NO_SOLUTION")
            continue

        trace, ans = column_trace(expr, sols[0])
        out.append(f"P{idx}:{expr}|{trace}|{ans}")

    return "\n".join(out)

if __name__ == "__main__":
    examples = [
        ("SEND+MORE=MONEY", "TWO+TWO=FOUR"),
        ("BASE+BALL=GAMES", "CROSS+ROADS=DANGER"),
    ]

    for a, b in examples:
        print("-----")
        print(solve_dual(a, b))
