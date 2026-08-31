# SigilAGI — Gemma 4 Good Hackathon

Object-to-glyph detection for real-world understanding, symbolic compression, and accessible AI reasoning.

## Project Summary

SigilAGI is an AI system that detects real-world objects, converts them into symbolic glyph representations, and uses Gemma 4 to reason over those glyphs.

Instead of only describing a scene in plain language, SigilAGI creates a structured symbolic layer:

- Object detected
- Object role
- Scene relationship
- Glyph assignment
- Meaning cluster
- Risk or importance level
- Human-readable explanation

## Core Concept

SigilAGI turns visual objects into glyph-based intelligence.

Example:

```text
Detected object: Door
Glyph: ⛩
Meaning: Entry / exit / boundary / transition
Scene role: Possible access point
Reasoning note: This object may define movement, separation, or containment.
Why It Matters
Many AI systems describe images but do not create reusable symbolic structures from them.
SigilAGI introduces an object-to-glyph layer that can help with:
Visual reasoning
Accessibility
Scene memory
Compression
Pattern recognition
Assistive navigation
Field documentation
Human-readable AI traces
Gemma 4 Usage
Gemma 4 is used for:
Interpreting detected objects
Assigning symbolic meaning
Generating glyph-based summaries
Explaining object relationships
Building structured scene reports
Translating glyph clusters into plain English
Supporting agentic reasoning over visual inputs
Object-to-Glyph Detection Pipeline
Plain text
Image Input
   ↓
Object Detection
   ↓
Object Label Extraction
   ↓
Glyph Mapping
   ↓
Scene Relationship Graph
   ↓
Gemma 4 Reasoning
   ↓
Glyph Report + Plain-English Summary
Example Output
JSON
{
  "scene": "indoor room",
  "objects": [
    {
      "label": "door",
      "glyph": "⛩",
      "meaning": "boundary / transition / access",
      "role": "entry point"
    },
    {
      "label": "phone",
      "glyph": "☏",
      "meaning": "communication / signal / record",
      "role": "information device"
    },
    {
      "label": "person",
      "glyph": "☉",
      "meaning": "actor / observer / intent",
      "role": "human subject"
    }
  ],
  "glyph_summary": "☉ near ☏ facing ⛩",
  "plain_english": "A person is near a communication device and positioned toward an entry or boundary point."
}
Safety Design
SigilAGI separates what is detected from what is inferred.
Every report marks:
Detected — objects directly identified from the image
Mapped — glyphs assigned to those objects
Inferred — possible meanings or relationships
Unknown — things the system cannot verify
Human review needed — anything uncertain or high-impact
Demo Flow
User uploads an image.
Object detection identifies objects.
SigilAGI maps each object to a glyph.
Gemma 4 explains the symbolic scene.
The app returns a glyph report and plain-language summary.
Repository Structure
Plain text
app/                  Demo application
examples/             Sample inputs and outputs
docs/                 Supporting documentation
assets/               Images, logos, screenshots
scripts/              Setup and utility scripts
README.md             Project overview
architecture.md       Technical architecture
demo_script.md        Video/demo script
submission_writeup.md Hackathon submission writeup
requirements.txt      Python dependencies
Status
Hackathon build in progress.

## Links

- GitHub Repository: https://github.com/Nine1Eight/gemma4good-sigilagi
- Local Demo: http://127.0.0.1:7861
- Hackathon Target: Gemma 4 Good Hackathon

## Live Demo

- Hugging Face Space: https://huggingface.co/spaces/Nine1Eight/gemma4good-sigilagi
