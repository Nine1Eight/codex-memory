#!/usr/bin/env python3
"""
SigilAGI Gemma Reasoning Layer

Termux-safe optional bridge for local Gemma reasoning through Ollama.

Works in two modes:

1. Offline fallback:
   Generates a deterministic reasoning summary without external dependencies.

2. Ollama mode:
   Sends the SigilAGI report to a local Ollama Gemma model if available.

Environment variables:
- SIGILAGI_OLLAMA_URL
- SIGILAGI_MODEL
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from sigilagi_core import generate_report


OLLAMA_URL = os.environ.get("SIGILAGI_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.environ.get("SIGILAGI_MODEL", "gemma")


def build_prompt(report: Dict[str, Any]) -> str:
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
1. Detected Scene
2. Glyph Interpretation
3. Possible Meaning
4. Unknowns
5. Human Review Notes
""".strip()


def deterministic_reasoning(report: Dict[str, Any]) -> str:
    objects = report.get("detected_objects", [])
    glyph_summary = report.get("glyph_summary", "")
    plain = report.get("plain_english_summary", "")
    risks = report.get("risk_flags", [])
    unknowns = report.get("unknowns", [])
    relationships = report.get("relationships", [])

    lines = []

    lines.append("Detected Scene:")
    if objects:
        lines.append("- Objects detected or provided: " + ", ".join(objects) + ".")
    else:
        lines.append("- No objects were detected or provided.")

    lines.append("")
    lines.append("Glyph Interpretation:")
    lines.append(f"- Glyph trace: {glyph_summary or 'none'}.")

    if relationships:
        for rel in relationships:
            lines.append(f"- {rel.get('symbolic', '')}: {rel.get('plain', '')}")
    else:
        lines.append("- No strong symbolic relationships were generated.")

    lines.append("")
    lines.append("Possible Meaning:")
    lines.append(f"- {plain}")

    lines.append("")
    lines.append("Unknowns:")
    for item in unknowns:
        lines.append(f"- {item}")

    lines.append("")
    lines.append("Human Review Notes:")
    if risks:
        for risk in risks:
            lines.append(f"- {risk}")
    else:
        lines.append("- No high-review or privacy-review flags were generated.")

    lines.append("- Treat this as an organized symbolic reasoning trace, not proof.")

    return "\n".join(lines)


def call_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        return parsed.get("response", "").strip()


def reason_over_report(report: Dict[str, Any], use_ollama: bool = False) -> Dict[str, Any]:
    prompt = build_prompt(report)

    if use_ollama:
        try:
            model_output = call_ollama(prompt)
            if not model_output:
                model_output = deterministic_reasoning(report)
            model_status = "ollama_success"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, Exception) as exc:
            model_output = deterministic_reasoning(report)
            model_status = f"ollama_unavailable_fallback_used: {type(exc).__name__}: {exc}"
    else:
        model_output = deterministic_reasoning(report)
        model_status = "deterministic_fallback"

    return {
        "project": "SigilAGI",
        "reasoning_mode": model_status,
        "model_target": OLLAMA_MODEL if use_ollama else "none",
        "prompt": prompt,
        "reasoning_output": model_output
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SigilAGI Gemma reasoning layer")
    parser.add_argument(
        "--labels",
        required=True,
        help="Comma-separated object labels, example: 'person, phone, door'"
    )
    parser.add_argument(
        "--note",
        default="",
        help="Optional scene note"
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="Try local Ollama Gemma reasoning, then fall back if unavailable"
    )

    args = parser.parse_args()

    report = generate_report(args.labels, args.note)
    reasoning = reason_over_report(report, use_ollama=args.ollama)

    bundle = {
        "sigilagi_report": report,
        "gemma_reasoning_layer": reasoning
    }

    print(json.dumps(bundle, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
