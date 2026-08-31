from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

_BOXED_RE = re.compile(r"\\boxed\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
_LATEX_SPACING_RE = re.compile(r"\\(?:,|;|:|!|\s)")


def strip_boxed(text: Any) -> str:
    """Extract the final boxed answer when present; otherwise stringify."""
    if text is None:
        return ""
    s = str(text).strip()
    matches = list(_BOXED_RE.finditer(s))
    if matches:
        return matches[-1].group(1).strip()
    return s


def normalize_answer(text: Any) -> str:
    """Canonicalize answer strings for exact-match style training.

    This intentionally avoids semantic guessing. It removes wrappers, obvious
    formatting noise, and normalizes integers/fractions/decimals conservatively.
    """
    s = strip_boxed(text)
    s = s.replace("$", "").strip()
    s = _LATEX_SPACING_RE.sub("", s)
    s = s.replace("\\left", "").replace("\\right", "")
    s = s.replace("\\cdot", "*").replace("×", "*").replace("÷", "/")
    s = re.sub(r"\s+", " ", s).strip()

    # Drop trailing punctuation that often appears after final answers.
    s = s.rstrip(" .,")

    # Canonical integers, including +0007 => 7.
    if re.fullmatch(r"[+-]?\d+", s):
        return str(int(s))

    # Canonical simple fractions.
    if re.fullmatch(r"[+-]?\d+\s*/\s*[+-]?\d+", s):
        try:
            return str(Fraction(s.replace(" ", "")))
        except ZeroDivisionError:
            return s.replace(" ", "")

    # Canonical finite decimals without destructive rounding.
    if re.fullmatch(r"[+-]?\d+\.\d+", s):
        sign = "-" if s.startswith("-") else ""
        body = s[1:] if s[0:1] in "+-" else s
        whole, frac = body.split(".", 1)
        whole = str(int(whole or "0"))
        frac = frac.rstrip("0")
        return sign + whole if not frac else sign + whole + "." + frac

    return s


def boxed(answer: Any) -> str:
    return "\\boxed{" + normalize_answer(answer) + "}"


def answer_equal(a: Any, b: Any) -> bool:
    return normalize_answer(a) == normalize_answer(b)
