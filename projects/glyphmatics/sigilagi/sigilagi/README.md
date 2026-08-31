# SigilAGI — Canonical Glyphmatic System

This repository defines a lossless, deterministic encoding system that maps
any computable artifact (any size, any type) into a single tri-sigil composed
of three glyphs drawn from three fixed canons of size 111.

Invariant:
    expand(collapse(F)) == F
    collapse(expand(S)) == S

Artifacts:
- The ASCII glyph field is the stored system.
- The tri-sigil is the executable address.

This repository contains:
- Canon definitions (3 × 111 glyphs)
- Encoder (stream → visible field)
- Collapse (field → tri-sigil)
- Expansion (tri-sigil → field)
- Formal invariants and diagrams

The system is canon-pure, deterministic, and idempotent.
