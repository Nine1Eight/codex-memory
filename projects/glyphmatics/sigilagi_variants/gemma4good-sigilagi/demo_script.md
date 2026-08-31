# SigilAGI Demo Script

## Project

SigilAGI — Object-to-Glyph Detection for Gemma 4 Good

## Tagline

Object-to-glyph detection for symbolic AI reasoning.

---

## 3-Minute Demo Flow

### 0:00–0:20 — Problem

Most vision AI systems describe images in plain language, but they do not create a reusable symbolic reasoning layer.

SigilAGI introduces a middle layer:

```text
object → glyph → meaning → relationship → reasoning trace
This makes scene understanding more compact, inspectable, and human-reviewable.
0:20–0:50 — Core Idea
The system takes detected objects such as:
Plain text
person, phone, door, wallet, paper
Then converts them into symbolic glyphs:
Plain text
☉ → ☏ → ⛩ → ▨ → ▧
Each glyph carries meaning:
☉ = actor / observer / human subject
☏ = communication / signal / record
⛩ = boundary / entry / exit
▨ = identity / value / personal property
▧ = document / record / instruction
0:50–1:30 — Live Demo
Open the local demo:
Plain text
http://127.0.0.1:7860
Input:
Plain text
person, phone, door, wallet, paper
Scene note:
Plain text
Demo scene for object-to-glyph symbolic reasoning.
Click:
Plain text
Generate SigilAGI Report
Show the output:
Plain text
☉ → ☏ → ⛩ → ▨ → ▧
Then show the plain-English explanation and structured JSON.
1:30–2:10 — Gemma 4 Reasoning Layer
SigilAGI builds a structured report and sends it into a Gemma-ready reasoning prompt.
Gemma 4 is used to explain:
Detected scene
Glyph interpretation
Possible meaning
Unknowns
Human-review notes
The system is designed so Gemma reasons over structured symbolic input instead of raw labels alone.
2:10–2:40 — Safety
SigilAGI separates:
Detected objects
Symbolic mappings
Possible meanings
Unknowns
Human-review warnings
It does not claim:
Identity
Intent
Guilt
Legal conclusions
Medical conclusions
Exact danger level
2:40–3:00 — Impact
SigilAGI can support:
Assistive scene understanding
Accessibility
Symbolic compression
Edge AI workflows
Human-readable AI traces
Safer visual reasoning systems
Closing line:
Plain text
SigilAGI turns object detection into symbolic reasoning that humans can inspect, verify, and improve.EOF
