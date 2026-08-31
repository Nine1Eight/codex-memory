#!/usr/bin/env python3
"""
SigilAGI Hugging Face Space App

This file is intended for Hugging Face Spaces.

Local Termux users should run:

./scripts/run_demo.sh
"""

import sys
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from sigilagi_core import generate_report
from gemma_reasoner import reason_over_report


DEFAULT_LABELS = "person, phone, door, wallet, paper"
DEFAULT_NOTE = "Gemma 4 Good demo scene for object-to-glyph symbolic reasoning."


def analyze(labels: str, scene_note: str, use_reasoning_layer: bool):
    labels = (labels or "").strip()
    scene_note = (scene_note or "").strip()

    if not labels:
        report = {
            "error": "Enter at least one object label.",
            "example": "person, phone, door"
        }
        return "", "No object labels provided.", report, "No reasoning generated."

    report = generate_report(labels, scene_note)

    glyph_summary = report.get("glyph_summary", "")
    plain_summary = report.get("plain_english_summary", "")

    if use_reasoning_layer:
        reasoning = reason_over_report(report, use_ollama=False)
        reasoning_text = reasoning.get("reasoning_output", "")
    else:
        reasoning_text = "Reasoning layer disabled. Enable it to generate the structured SigilAGI explanation."

    return glyph_summary, plain_summary, report, reasoning_text


with gr.Blocks(title="SigilAGI — Object-to-Glyph Detection") as demo:
    gr.Markdown(
        """
# SigilAGI 🧬

**Object-to-glyph detection for symbolic AI reasoning.**

SigilAGI converts detected objects into glyphs, meanings, scene roles, relationships, unknowns, and human-review notes.

## Core Transformation

```text
object → glyph → meaning → relationship → reasoning trace
""" )
with gr.Row():
    with gr.Column():
        labels = gr.Textbox(
            label="Detected object labels",
            value=DEFAULT_LABELS,
            lines=4,
            placeholder="person, phone, door"
        )

        note = gr.Textbox(
            label="Optional scene note",
            value=DEFAULT_NOTE,
            lines=3
        )

        use_reasoning_layer = gr.Checkbox(
            label="Enable SigilAGI reasoning layer",
            value=True
        )

        button = gr.Button("Generate SigilAGI Report")

    with gr.Column():
        glyph_summary = gr.Textbox(
            label="Glyph Summary",
            lines=2
        )

        plain_summary = gr.Textbox(
            label="Plain-English Summary",
            lines=6
        )

report_json = gr.JSON(label="Structured JSON Report")

reasoning_output = gr.Textbox(
    label="Gemma-Ready Reasoning Output",
    lines=18
)

button.click(
    fn=analyze,
    inputs=[labels, note, use_reasoning_layer],
    outputs=[glyph_summary, plain_summary, report_json, reasoning_output]
)

gr.Examples(
    examples=[
        ["person, phone, door, wallet, paper", "Basic symbolic reasoning demo.", True],
        ["person, vehicle, key, bag", "Access and movement scene.", True],
        ["camera, face, document, light", "Privacy-sensitive documentation scene.", True],
        ["person, knife, door", "High-review object demo.", True]
    ],
    inputs=[labels, note, use_reasoning_layer],
    outputs=[glyph_summary, plain_summary, report_json, reasoning_output],
    fn=analyze,
    cache_examples=False
)

gr.Markdown(
    """
Safety Boundary
SigilAGI does not prove identity, intent, guilt, legal status, medical status, or confirmed danger.
It creates an organized symbolic reasoning trace for human review. """ )
if name == "main": demo.launch()
