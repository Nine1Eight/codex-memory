# Kaggle Form Answers — SigilAGI

## Project Title

SigilAGI — Object-to-Glyph Detection for Symbolic AI Reasoning

## Short Description

SigilAGI converts detected objects into glyphs, meanings, scene roles, relationships, unknowns, and human-review notes. It gives Gemma a structured symbolic trace to reason over instead of raw labels alone.

## Public GitHub Repository

https://github.com/Nine1Eight/gemma4good-sigilagi

## Live Demo

https://huggingface.co/spaces/Nine1Eight/gemma4good-sigilagi

## Video Demo

https://www.youtube.com/watch?v=-zY6nOSD8Sg

## What Problem Does This Solve?

Most vision AI systems stop at plain image captions. SigilAGI adds a symbolic reasoning layer that makes object detection more inspectable, compressible, and human-reviewable.

The system transforms:

object → glyph → meaning → relationship → reasoning trace

This can support accessibility, assistive scene understanding, field documentation, edge AI workflows, and safer visual reasoning.

## How Does It Use Gemma?

SigilAGI creates a structured object-to-glyph report, then sends that report into a Gemma-ready reasoning prompt.

Gemma receives:

- Detected object labels
- Object-to-glyph mappings
- Symbolic meanings
- Scene relationships
- Risk flags
- Unknowns
- Human-review instructions

Gemma then generates:

- Detected scene summary
- Glyph interpretation
- Possible meaning
- Unknowns
- Human-review notes

## Why Is It Useful?

SigilAGI makes AI vision outputs easier to inspect and verify. Instead of producing only a caption, it produces a structured symbolic trace that humans can review.

Example:

Input:
person, phone, door, wallet, paper

Glyph trace:
☉ → ☏ → ⛩ → ▨ → ▧

Meaning:
A human subject, communication object, access boundary, personal property object, and document object appear in the same scene.

## Safety Boundary

SigilAGI does not prove identity, intent, guilt, legal status, medical status, or confirmed danger.

It separates:

1. Detected objects
2. Symbolic mappings
3. Possible meanings
4. Unknowns
5. Human-review warnings

Privacy-sensitive and high-review objects are flagged.

## Technical Summary

Core files:

- app/sigilagi_core.py
- app/gemma_reasoner.py
- app/simple_web_app.py
- app.py
- docs/glyph_schema.md
- docs/gemma_reasoning_prompt.md
- examples/demo_output.json

## Final Pitch

SigilAGI turns object detection into symbolic reasoning. It gives Gemma a structured glyph layer to reason over while keeping the output inspectable, safety-aware, and reviewable by humans.
