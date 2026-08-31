# SigilAGI — Gemma 4 Good Hackathon Submission

## Summary

SigilAGI is an object-to-glyph detection system that converts detected real-world objects into symbolic glyph structures, then uses a Gemma-ready reasoning layer to explain the scene in a clear, inspectable, and safety-aware format.

Instead of stopping at image captioning, SigilAGI introduces a symbolic middle layer:

```text
object → glyph → meaning → relationship → reasoning trace
This makes visual reasoning more compact, auditable, and reusable.
Problem
Modern AI vision systems can describe a scene, but their reasoning is often difficult to inspect.
A caption such as:
Plain text
A person is near a phone and a door.
is useful, but it does not preserve a structured symbolic trace.
SigilAGI solves this by mapping detected objects into glyph records that contain:
Object label
Glyph
Meaning
Scene role
Risk or review level
Relationship trace
Unknowns
Human-review notes
Solution
SigilAGI takes object labels from a detector or user input and converts them into symbolic glyph objects.
Example input:
Plain text
person, phone, door, wallet, paper
Example glyph output:
Plain text
☉ → ☏ → ⛩ → ▨ → ▧
Example interpretation:
Plain text
A human subject, communication object, access boundary, personal property object, and document object are present in the same scene.
The system then generates a structured JSON report and a reasoning output suitable for Gemma 4.
Gemma 4 Usage
Gemma 4 is used as the reasoning layer over SigilAGI's structured glyph report.
The model receives:
Detected objects
Glyph mappings
Relationship traces
Risk flags
Unknowns
Safety instructions
Gemma 4 then produces a concise explanation with:
Detected Scene
Glyph Interpretation
Possible Meaning
Unknowns
Human Review Notes
This approach reduces hallucination risk because the model is instructed to reason only from the structured report.
Technical Architecture
The system contains these components:
Plain text
Image or label input
   ↓
Object detection or manual labels
   ↓
Object-to-glyph mapper
   ↓
Relationship generator
   ↓
Structured JSON report
   ↓
Gemma 4 reasoning prompt
   ↓
Human-readable explanation
Current implementation:
app/sigilagi_core.py — core object-to-glyph engine
app/gemma_reasoner.py — Gemma/Ollama-ready reasoning bridge with deterministic fallback
app/simple_web_app.py — dependency-free Termux-safe web demo
docs/glyph_schema.md — glyph schema
docs/gemma_reasoning_prompt.md — Gemma reasoning prompt
examples/demo_input.json — sample input
examples/demo_output.json — sample output
Safety Design
SigilAGI avoids unsafe certainty.
The system does not claim:
Identity
Intent
Guilt
Legal status
Medical status
Exact danger level
The report separates:
Detected facts
Symbolic mappings
Possible meanings
Unknowns
Human-review warnings
High-impact or privacy-sensitive objects are flagged for review.
Example:
Plain text
Privacy-sensitive object detected: wallet mapped to ▨.
Why It Matters
SigilAGI demonstrates that visual AI can be more than caption generation.
It can create symbolic structures that support:
Accessibility
Assistive navigation
Field documentation
Scene memory
Object relationship analysis
Transparent AI traces
Edge AI reasoning
Human-review workflows
Current Demo
The local demo runs with no external Python dependencies:
Bash
./scripts/run_demo.sh
Then open:
Plain text
http://127.0.0.1:7860
The CLI reasoning layer runs with:
Bash
python app/gemma_reasoner.py \
  --labels "person, phone, door, wallet, paper" \
  --note "SigilAGI demo"
Optional local Gemma/Ollama mode:
Bash
SIGILAGI_MODEL=gemma python app/gemma_reasoner.py \
  --labels "person, phone, door, wallet, paper" \
  --note "SigilAGI local Gemma test" \
  --ollama
If Ollama is unavailable, the system falls back to deterministic reasoning.
Future Work
Next build stages:
Connect live object detection from images.
Add bounding-box relationship extraction.
Expand the glyph schema.
Add vector memory for repeated scene patterns.
Deploy a Hugging Face Space demo.
Add mobile camera frame ingestion.
Add Gemma 4 local inference packaging.
Closing
SigilAGI turns object detection into symbolic reasoning.
It gives Gemma 4 a structured glyph layer to reason over, while preserving human review, safety boundaries, and transparent output.
