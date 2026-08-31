from __future__ import annotations

from .schemas import ValueProducts, ValueVector


def products(vector: ValueVector, mode: str) -> ValueProducts:
    values = tuple(getattr(vector, name) for name in ("C","R","G","H","T","U","KG","E","X","F","P"))
    if any(not 0 <= value <= 1 for value in values): raise ValueError("value vector entries must be in [0,1]")
    epistemic = 0.30*vector.KG + 0.25*vector.E + 0.20*vector.X + 0.15*vector.U + 0.10*vector.H
    strategic = 0.22*vector.C + 0.22*vector.R + 0.18*vector.G + 0.10*vector.T + 0.10*vector.P + 0.08*vector.H - 0.10*vector.F
    if mode == "exploit": decision = 0.25*epistemic + 0.75*strategic
    elif mode == "recover": decision = 0.60*epistemic + 0.40*strategic
    else: decision = 0.55*epistemic + 0.45*strategic
    return ValueProducts(epistemic, strategic, decision, vector, mode)
