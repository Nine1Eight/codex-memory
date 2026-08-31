#!/usr/bin/env python3
"""
SigilAGI Gradio Demo

Purpose:
Interactive demo for object-to-glyph detection and symbolic reasoning.

Input:
- Comma-separated object labels
- Optional scene note

Output:
- Glyph summary
- Plain-English summary
- Structured JSON report
- Optional local Gemma/Ollama reasoning if Ollama is running
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import gradio as gr
import requests

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from sigilagi_core import generate_report


OLLAMA_URL = os.environ.get("SIGILAGI_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.environ.get("SIGILAGI_MODEL", "gemma")


def build_gemma_prompt(report: Dict[str, Any]) -> str:
    return f"""
You are SigilAGI, an object-to-glyph reasoning assistant.

Task:
Explain the symbolic scene report using clear, careful, safety-aware language.

Rules:
- Do not invent objects.
- Do not identify people.
- Do not claim intent, guilt, legal status, or medical status.
- Separate detected facts from symbolic interpretation.
- Use concise language.
- Mention human review when uncertainty or risk appears.

Structured report:
{json.dumps(report, ensure_ascii=False, indent=2)}

Return:
1. Detected scene
2. Glyph interpretation
3. Possible meaning
4. Unknowns
5. Human-review notes
""".strip()


def run_ollama_reasoning(report: Dict[str, Any]) -> str:
    prompt = build_gemma_prompt(report)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip() or "Ollama returned an empty response."
    except Exception as exc:
        return (
            "Local Gemma/Ollama reasoning was not available.\n\n"
            f"Reason: {type(exc).__name__}: {exc}\n\n"
            "The core SigilAGI object-to-glyph report still generated successfully."
        )


def analyze_scene(labels: str, scene_note: str, use_local_model: bool):
    labels = labels.strip()
    scene_note = scene_note.strip()

    if not labels:
        empty = {
            "error": "Enter at least one object label, for example: person, phone, door"
        }
        return "", "No labels provided.", json.dumps(empty, indent=2), "No model call made."

    report = generate_report(labels, scene_note)

    glyph_summary = report.get("glyph_summary", "")
    plain_summary = report.get("plain_english_summary", "")
    report_json = json.dumps(report, ensure_ascii=False, indent=2)

    if use_local_model:
        model_reasoning = run_ollama_reasoning(report)
    else:
        model_reasoning = "Local model reasoning disabled. Enable the checkbox after starting Ollama with a Gemma model."

    return glyph_summary, plain_summary, report_json, model_reasoning


EXAMPLE_LABELS = "person, phone, door, wallet, paper"
EXAMPLE_NOTE = "Demo image labels for object-to-glyph symbolic reasoning."


with gr.Blocks(title="SigilAGI Object-to-Glyph Detection") as demo:
    gr.Markdown(
        """
# SigilAGI — Object-to-Glyph Detection 🧬

Convert detected objects into glyphs, symbolic scene traces, and readable reasoning reports.

This demo accepts object labels directly. A production build can connect the same core engine to an image object detector.
"""
    )

    with gr.Row():
        with gr.Column():
            labels = gr.Textbox(
                label="Detected object labels",
                value=EXAMPLE_LABELS,
                lines=3,
                placeholder="person, phone, door"
            )

            scene_note = gr.Textbox(
                label="Optional scene note",
                value=EXAMPLE_NOTE,
                lines=3
            )

            use_local_model = gr.Checkbox(
                label="Use local Gemma/Ollama reasoning",
                value=False
            )

            run_button = gr.Button("Generate SigilAGI Report")

        with gr.Column():
            glyph_summary = gr.Textbox(label="Glyph Summary")
            plain_summary = gr.Textbox(label="Plain-English Summary", lines=5)

    with gr.Row():
        report_json = gr.Code(label="Structured JSON Report", language="json")
        model_reasoning = gr.Textbox(label="Gemma Reasoning Layer", lines=18)

    run_button.click(
        fn=analyze_scene,
        inputs=[labels, scene_note, use_local_model],
        outputs=[glyph_summary, plain_summary, report_json, model_reasoning]
    )

    gr.Markdown(
        """
## Safety Boundary

SigilAGI does not prove identity, intent, guilt, danger, legal status, or medical status.  
It organizes detections into symbolic structure for human review.
"""
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
