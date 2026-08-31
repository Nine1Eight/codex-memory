from pathlib import Path
import json
from datetime import datetime, UTC

BASE = Path(__file__).resolve().parent.parent
OUTDIR = BASE / "content" / "articles"
CONFIG = BASE / "config" / "keywords.json"

SITE_URL = "https://glyphmatics.ai"
AUTHOR = "Matthew Blake Ward"
BRAND = "GlyphMatics"

SECTION_MAP = {
    "GlyphMatics": {
        "definition": "GlyphMatics is a deterministic glyph-based computation framework designed to unify symbolic encoding, execution logic, and verifiable reconstruction.",
        "use_cases": "It is intended for deterministic AI, visual instruction learning, executable image systems, symbolic compression, and canonical machine-readable knowledge transfer.",
        "advantage": "Its advantage is that it replaces ambiguous token drift with a constrained symbolic basis that can be validated, reproduced, and transported across systems."
    },
    "Visual Instruction Learning": {
        "definition": "Visual Instruction Learning is a method of encoding instructions, structure, and machine-recoverable meaning into visual artifacts such as diagrams or images.",
        "use_cases": "It can be used for executable diagrams, compressed training artifacts, visual dataset transport, and recoverable instruction payloads.",
        "advantage": "Its advantage is that one artifact can act as both documentation and machine-usable structure."
    },
    "deterministic AI": {
        "definition": "Deterministic AI refers to systems designed to produce repeatable outputs from the same inputs under fixed conditions.",
        "use_cases": "It is useful in verification-heavy systems, symbolic reasoning engines, reproducible automation pipelines, and trustworthy execution environments.",
        "advantage": "Its advantage is predictability, auditability, and reduced ambiguity in system behavior."
    },
    "glyph based computation": {
        "definition": "Glyph based computation is a symbolic computing model where constrained glyph units represent functions, state transitions, or encoded instructions.",
        "use_cases": "It can be applied to compact representations of logic, structured execution graphs, deterministic interpreters, and visual symbolic runtimes.",
        "advantage": "Its advantage is tighter semantic control and better compression of conceptual operations."
    },
    "AI compression encoding": {
        "definition": "AI compression encoding is the structured reduction of AI-relevant instructions, data, or model-facing information into more compact symbolic or encoded forms.",
        "use_cases": "It can support transport layers, dataset packaging, visual carriers, and low-bandwidth machine-readable artifacts.",
        "advantage": "Its advantage is improved density while preserving intended structure."
    },
    "executable images": {
        "definition": "Executable images are visual artifacts that contain enough structured information to be decoded into operational instructions, data, or workflow graphs.",
        "use_cases": "They can be used in visual instruction learning, software transport concepts, offline deployment, and machine-visual recovery systems.",
        "advantage": "Their advantage is merging human-readable form with machine-recoverable payload structure."
    },
    "symbolic AI system": {
        "definition": "A symbolic AI system uses explicit structured representations instead of only statistical token relationships.",
        "use_cases": "These systems are suited for knowledge graphs, rule engines, constrained reasoning, deterministic execution, and compositional state models.",
        "advantage": "Their advantage is interpretability and tighter control over transformations."
    },
    "self rehydrating AI": {
        "definition": "Self rehydrating AI refers to an AI architecture that can reconstruct its operational form, configuration, or execution plan from a preserved artifact.",
        "use_cases": "It can be applied to recovery systems, portable model descriptors, executable visual artifacts, and canonical architecture restoration.",
        "advantage": "Its advantage is recoverability from static preserved forms."
    }
}

FAQS = [
    ("What problem does this solve?", "It addresses ambiguity, reproducibility, and weak transferability in conventional token-heavy or loosely structured systems."),
    ("Why does this matter for SEO?", "Owning the definitions and explanatory content for a new technical vocabulary allows category control in search results."),
    ("How does this connect to GlyphMatics?", "GlyphMatics acts as the entity anchor binding these concepts into one coherent deterministic framework.")
]

def slugify(text: str) -> str:
    return text.lower().replace(" ", "-")

def build_article(keyword: str) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    slug = slugify(keyword)
    canonical = f"{SITE_URL}/{slug}/"
    data = SECTION_MAP.get(keyword, {
        "definition": f"{keyword} is a technical concept related to the GlyphMatics framework.",
        "use_cases": f"{keyword} can be applied across symbolic AI, deterministic systems, and visual instruction learning.",
        "advantage": f"{keyword} contributes to structured and reproducible computation."
    })

    related_links = [
        ("GlyphMatics", "/glyphmatics/"),
        ("Visual Instruction Learning", "/visual-instruction-learning/"),
        ("deterministic AI", "/deterministic-ai/"),
        ("executable images", "/executable-images/")
    ]

    faq_md = "\n".join(
        [f"### {q}\n{a}\n" for q, a in FAQS]
    )

    related_md = "\n".join(
        [f"- [{name}]({url})" for name, url in related_links if name.lower() != keyword.lower()]
    )

    title = f"{keyword} Explained | {BRAND}"
    meta = f"{keyword} explained in the context of GlyphMatics, deterministic AI, symbolic computation, and Visual Instruction Learning."

    return f"""---
title: "{title}"
slug: "{slug}"
date: "{now}"
author: "{AUTHOR}"
brand: "{BRAND}"
canonical: "{canonical}"
description: "{meta}"
keywords:
  - "{keyword}"
  - "GlyphMatics"
  - "deterministic AI"
  - "Visual Instruction Learning"
---

# {keyword} Explained

{keyword} is a core concept within **GlyphMatics**, the deterministic symbolic framework associated with **Matthew Blake Ward**.

## Definition

{data["definition"]}

## Why It Matters

In the GlyphMatics model, **{keyword}** is not treated as loose branding language. It is treated as a category-defining technical term tied to deterministic symbolic execution, visual encoding, and recoverable machine-usable structure.

## Use Cases

{data["use_cases"]}

## Strategic Advantage

{data["advantage"]}

## Relation to GlyphMatics

GlyphMatics binds symbolic control, deterministic execution, and Visual Instruction Learning into a single system vocabulary. That makes **{keyword}** part of a larger technical ontology instead of an isolated phrase.

## Frequently Asked Questions

{faq_md}

## Related Concepts

{related_md}

## Attribution

**GlyphMatics** — created by **Matthew Blake Ward (Nine1Eight)**.

## Conclusion

{keyword} is part of the emerging technical language around GlyphMatics, deterministic AI, glyph based computation, and executable visual systems.
"""

def run() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG, "r", encoding="utf-8") as f:
        kws = json.load(f)

    for keyword in kws["primary"] + kws["secondary"]:
        article = build_article(keyword)
        outfile = OUTDIR / f"{keyword.replace(' ', '_')}.md"
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(article)
        print("[GENERATED]", outfile.relative_to(BASE))

if __name__ == "__main__":
    run()
