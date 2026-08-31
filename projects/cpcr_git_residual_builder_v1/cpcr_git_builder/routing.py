from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List

ANCHOR_CATEGORIES = {
    "cipher",
    "text_cipher",
    "numeral",
    "numeral_system",
    "unit_conversion",
    "gravity",
    "physics_gravity",
}

STAGE1_CATEGORIES = {
    "equation_symbolic",
    "equation_numeric",
    "equation_numeric_deduce",
}

STAGE2_CATEGORIES = {
    "cryptarithm",
    "cryptarithm_deduce",
}

QUARANTINE_CATEGORIES = {
    "bit_manipulation",
    "equation_numeric_guess",
    "cryptarithm_guess",
    "unknown",
}

TRAIN_ALLOWLIST = ANCHOR_CATEGORIES | STAGE1_CATEGORIES | {"cryptarithm_deduce"}
TRAIN_DENYLIST = {
    "bit_manipulation",
    "equation_numeric_guess",
    "cryptarithm_guess",
    "unknown",
}

CATEGORY_PRIORS: Dict[str, float] = {
    "cipher": 1.00,
    "text_cipher": 1.00,
    "numeral": 1.00,
    "numeral_system": 1.00,
    "unit_conversion": 1.00,
    "gravity": 0.9826,
    "physics_gravity": 0.9826,
    "equation_symbolic": 0.9720,
    "equation_numeric_deduce": 0.91,
    "equation_numeric": 0.8939,
    "cryptarithm_deduce": 0.86,
    "cryptarithm": 0.8243,
    "bit_manipulation": 0.2639,
    "equation_numeric_guess": 0.25,
    "cryptarithm_guess": 0.20,
    "unknown": 0.05,
}

@dataclass(frozen=True)
class RouteDecision:
    category: str
    stage: int
    train_allowed: bool
    confidence_prior: float
    reason: str


def infer_category(prompt: str) -> str:
    p = (prompt or "").lower()

    if any(k in p for k in ["caesar", "cipher", "decrypt", "encrypt", "substitution"]):
        return "cipher"
    if any(k in p for k in ["binary", "base", "hexadecimal", "octal", "roman numeral"]):
        return "numeral_system"
    if re.search(r"\b(km|kilometer|meter|metre|cm|kg|gram|hour|minute|second|mph|m/s)\b", p):
        return "unit_conversion"
    if any(k in p for k in ["gravity", "gravitational", "planet", "mass", "radius"]):
        return "physics_gravity"
    if any(k in p for k in ["cryptarithm", "alphametic"]):
        return "cryptarithm_deduce"
    if re.search(r"\b[A-Z]{1,8}\s*\+\s*[A-Z]{1,8}\s*=\s*[A-Z]{1,10}\b", prompt or ""):
        return "cryptarithm_deduce"
    if any(k in p for k in ["bitwise", " xor ", " and ", " or ", "left shift", "right shift", "<<", ">>"]):
        return "bit_manipulation"
    if any(k in p for k in ["solve for", "simplify", "factor", "expand", "derivative"]):
        return "equation_symbolic"
    if re.search(r"\d+\s*[+\-*/^]\s*\d+", p) or any(k in p for k in ["calculate", "compute", "what is"]):
        return "equation_numeric"
    return "unknown"


def route_category(category: str, verified: bool = False) -> RouteDecision:
    if category in ANCHOR_CATEGORIES:
        return RouteDecision(category, 0, True, CATEGORY_PRIORS.get(category, 0.9), "anchor_lock")
    if category in STAGE1_CATEGORIES:
        allowed = category != "equation_numeric_guess"
        return RouteDecision(category, 1, allowed, CATEGORY_PRIORS.get(category, 0.8), "symbolic_numeric_expand")
    if category in STAGE2_CATEGORIES:
        allowed = verified or category == "cryptarithm_deduce"
        return RouteDecision(category, 2, allowed, CATEGORY_PRIORS.get(category, 0.7), "verified_repair")
    if category in QUARANTINE_CATEGORIES:
        # Bit manipulation may become trainable only if exact-verifier says yes.
        allowed = verified and category == "bit_manipulation"
        return RouteDecision(category, 3, allowed, CATEGORY_PRIORS.get(category, 0.2), "quarantine_verified_only")
    return RouteDecision("unknown", 4, False, CATEGORY_PRIORS["unknown"], "unknown_quarantine")


def sort_rows_cpcr(rows: Iterable[dict]) -> List[dict]:
    enriched = []
    for row in rows:
        category = row.get("category") or infer_category(row.get("prompt") or row.get("instruction") or "")
        verified = bool(row.get("verified", False))
        route = route_category(category, verified=verified)
        x = dict(row)
        x.update({
            "category": route.category,
            "cpcr_stage": route.stage,
            "train_allowed": route.train_allowed,
            "confidence_prior": route.confidence_prior,
            "route_reason": route.reason,
        })
        enriched.append(x)
    return sorted(enriched, key=lambda r: (r["cpcr_stage"], -float(r.get("confidence_prior", 0.0)), r.get("category", "")))
