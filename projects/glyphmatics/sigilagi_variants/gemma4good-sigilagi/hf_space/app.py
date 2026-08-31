#!/usr/bin/env python3
"""
SigilAGI Hugging Face Space App

Simple Gradio Interface version.
Avoids nested Blocks layout errors on Hugging Face Spaces.
"""

import json
import sys
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from sigilagi_core import generate_report
from gemma_reasoner import reason_over_report


def analyze(labels, scene_note, use_reasoning_layer):
    labels = (labels or "").strip()
    scene_note = (scene_note or "").strip()

    if not labels:
        return (
            "",
            "No object labels provided.",
            {"error": "Enter at least one object label.", "example": "person, phone, door"},
            "No reasoning generated."
        )

    report = generate_report(labels, scene_note)

    glyph_summary = report.get("glyph_summary", "")
    plain_summary = report.get("plain_english_summary", "")

    if use_reasoning_layer:
        reasoning = reason_over_report(report, use_ollama=False)
        reasoning_text = reasoning.get("reasoning_output", "")
    else:
        reasoning_text = "Reasoning layer disabled."

    return glyph_summary, plain_summary, report, reasoning_text


description = """
# SigilAGI 🧬

Object-to-glyph detection for symbolic AI reasoning.

SigilAGI converts detected objects into glyphs, meanings, scene roles, relationships, unknowns, and human-review notes.

Core transformation:

object → glyph → meaning → relationship → reasoning trace

Safety boundary: SigilAGI does not prove identity, intent, guilt, legal status, medical status, or confirmed danger.
"""


demo = gr.Interface(
    fn=analyze,
    title="SigilAGI — Object-to-Glyph Detection",
    description=description,
    inputs=[
        gr.Textbox(
            label="Detected object labels",
            value="person, phone, door, wallet, paper",
            lines=4
        ),
        gr.Textbox(
            label="Optional scene note",
            value="Gemma 4 Good demo scene for object-to-glyph symbolic reasoning.",
            lines=3
        ),
        gr.Checkbox(
            label="Enable SigilAGI reasoning layer",
            value=True
        )
    ],
    outputs=[
        gr.Textbox(label="Glyph Summary", lines=2),
        gr.Textbox(label="Plain-English Summary", lines=6),
        gr.JSON(label="Structured JSON Report"),
        gr.Textbox(label="Gemma-Ready Reasoning Output", lines=18)
    ],
    examples=[
        ["person, phone, door, wallet, paper", "Basic symbolic reasoning demo.", True],
        ["person, vehicle, key, bag", "Access and movement scene.", True],
        ["camera, face, document, light", "Privacy-sensitive documentation scene.", True],
        ["person, knife, door", "High-review object demo.", True]
    ],
    cache_examples=False
)


if __name__ == "__main__":
    demo.launch()
