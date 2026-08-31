# SigilAGI — Gemma 4 Good Hackathon Submission

## Project Title

SigilAGI — Object-to-Glyph Detection for Symbolic AI Reasoning

## One-Line Summary

SigilAGI converts detected objects into glyphs, meanings, scene roles, relationships, unknowns, and human-review notes so Gemma can reason over a structured symbolic trace instead of raw labels alone.

## GitHub Repository

https://github.com/Nine1Eight/gemma4good-sigilagi

## Live Demo

https://huggingface.co/spaces/Nine1Eight/gemma4good-sigilagi

## Core Idea

Most vision systems stop at captions. SigilAGI adds a symbolic reasoning layer:

```text
object → glyph → meaning → relationship → reasoning trace
Example:
Plain text
person, phone, door, wallet, paper
becomes:
Plain text
☉ → ☏ → ⛩ → ▨ → ▧
This creates an inspectable structure that can be reviewed, compressed, reused, and explained.
How It Uses Gemma
Gemma is used as the reasoning layer over the SigilAGI structured report.
The system gives Gemma:
Detected object labels
Object-to-glyph mappings
Symbolic meanings
Scene relationships
Risk flags
Unknowns
Human-review instructions
Gemma then produces:
Detected scene summary
Glyph interpretation
Possible meaning
Unknowns
Human-review notes
Why It Matters
SigilAGI can support:
Accessibility
Assistive scene understanding
Symbolic compression
Edge AI workflows
Human-readable AI traces
Safer visual reasoning
Structured field documentation
AI systems that expose their reasoning inputs more clearly
Safety Boundary
SigilAGI does not prove:
Identity
Intent
Guilt
Legal status
Medical status
Confirmed danger
It separates detected objects from symbolic interpretation and marks privacy-sensitive or high-review objects for human review.
Demo Input
Plain text
person, phone, door, wallet, paper
Demo Output
Plain text
☉ → ☏ → ⛩ → ▨ → ▧
Demo Explanation
The scene contains a human subject, communication object, access boundary, personal property object, and document object. The system flags the wallet as privacy-sensitive and reminds the user that the report is an organized symbolic reasoning trace, not proof.
Technical Files
app/sigilagi_core.py — object-to-glyph engine
app/gemma_reasoner.py — Gemma-ready reasoning layer
app/simple_web_app.py — Termux-safe local web demo
app.py — Hugging Face Space Gradio app
docs/glyph_schema.md — glyph schema
docs/gemma_reasoning_prompt.md — Gemma prompt
examples/demo_input.json — example input
examples/demo_output.json — example output
submission_writeup.md — long-form submission writeup
demo_script.md — 3-minute video script
Final Pitch
SigilAGI turns object detection into symbolic reasoning. It gives Gemma a structured glyph layer to reason over while keeping the output inspectable, safety-aware, and reviewable by humans.
