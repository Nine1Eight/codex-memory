# SigilAGI Architecture

## Purpose

SigilAGI converts detected real-world objects into symbolic glyph structures, then uses Gemma 4 reasoning to explain the scene in both glyph form and plain language.

The goal is not just image captioning.

The goal is:

```text
object → glyph → meaning → relationship → reasoning trace
Core Pipeline
Plain text
Image Input
   ↓
Object Detection
   ↓
Detected Object List
   ↓
Object-to-Glyph Mapping
   ↓
Scene Relationship Graph
   ↓
Gemma 4 Reasoning Layer
   ↓
Glyph Report
   ↓
Plain-English Explanation
System Components
1. Image Input Layer
Accepts:
Uploaded image
Camera frame
Screenshot
Still frame from video
Output:
JSON
{
  "input_type": "image",
  "source": "user_upload"
}
2. Object Detection Layer
Detects visible objects in the image.
Example detected objects:
JSON
[
  {"label": "person", "confidence": 0.94},
  {"label": "door", "confidence": 0.87},
  {"label": "phone", "confidence": 0.81}
]
Initial demo implementation can use manual object labels or a lightweight detector.
Production implementation can connect to:
YOLO
OWL-ViT
Grounding DINO
Mobile vision models
Android camera frame detection
3. Object-to-Glyph Mapping Layer
Each detected object is converted into a symbolic glyph.
Example:
JSON
{
  "label": "door",
  "glyph": "⛩",
  "meaning": "boundary / entry / exit / transition",
  "role": "access point"
}
This layer gives the system a compressed symbolic structure instead of raw labels only.
4. Glyph Meaning Layer
Each glyph carries semantic meaning.
Example glyph meanings:
Object
Glyph
Meaning
person
☉
actor / observer / intent
door
⛩
boundary / transition / access
phone
☏
communication / signal / record
vehicle
⟡
movement / transport / force
bag
▣
container / carried item / storage
light
✦
visibility / signal / attention
weapon-like object
⚠
danger / review required
5. Scene Relationship Layer
SigilAGI builds simple symbolic relationships.
Example:
Plain text
☉ near ☏ facing ⛩
Plain meaning:
Plain text
A person is near a communication device and oriented toward an entry or boundary point.
Relationship types:
near
inside
outside
holding
facing
blocking
above
below
moving toward
separated from
6. Gemma 4 Reasoning Layer
Gemma 4 receives the detected objects, glyph mappings, and relationships.
It generates:
Glyph summary
Plain-English explanation
Risk flags
Unknowns
Human-review notes
Structured JSON report
Gemma 4 is not treated as an all-knowing source.
It reasons only from provided detections and user-supplied context.
Output Format
Final output uses this structure:
JSON
{
  "scene_type": "unknown",
  "detected_objects": [],
  "glyph_objects": [],
  "glyph_summary": "",
  "plain_english_summary": "",
  "risk_flags": [],
  "unknowns": [],
  "human_review_needed": []
}
Safety Rules
SigilAGI must separate:
Detected facts
Symbolic mappings
Inferences
Unknowns
Human-review warnings
The system must not claim:
Identity
Intent
Guilt
Legal conclusions
Medical conclusions
Certain danger from uncertain evidence
Use language like:
Plain text
Possible
Likely
Unclear
Needs human review
Not enough evidence
Hackathon Value
SigilAGI demonstrates how Gemma 4 can be used for:
Symbolic visual reasoning
Accessibility
Assistive scene understanding
Edge AI workflows
Transparent AI traces
Object-to-meaning compression
Human-readable reasoning reports
Minimal Demo Architecture
Plain text
Gradio UI
   ↓
User enters object labels or uploads image
   ↓
Python glyph mapper
   ↓
Gemma 4 prompt builder
   ↓
Structured report generator
   ↓
JSON + readable output
Future Architecture
Plain text
Camera / Image Source
   ↓
Real-time Object Detector
   ↓
Glyph Encoder
   ↓
Vector Memory
   ↓
Gemma 4 Agent
   ↓
Scene Reasoning
   ↓
User Report / API / Mobile App
