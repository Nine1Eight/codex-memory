#!/usr/bin/env python3
"""Build the self-contained Kaggle notebook from the reviewed attack module."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ATTACK_PATH = ROOT / "attack.py"
NOTEBOOK_PATH = ROOT / "ai-agent-security-adl-v2.ipynb"


def code_cell(source: str, cell_id: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def markdown_cell(source: str, cell_id: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def main() -> None:
    attack_code = ATTACK_PATH.read_text(encoding="utf-8")
    writer = f'''from __future__ import annotations

import hashlib
import py_compile
from pathlib import Path

WORK = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path.cwd()
WORK.mkdir(parents=True, exist_ok=True)
ATTACK_PATH = WORK / "attack.py"
ATTACK_CODE = {attack_code!r}

ATTACK_PATH.write_text(ATTACK_CODE, encoding="utf-8")
py_compile.compile(str(ATTACK_PATH), doraise=True)
assert "class AttackAlgorithm" in ATTACK_CODE
assert "def run(self, env" in ATTACK_CODE
assert "submission.csv" not in ATTACK_CODE.lower()
assert ".example/p" in ATTACK_CODE
print("WROTE_ATTACK_PY", ATTACK_PATH)
print("ATTACK_BYTES", ATTACK_PATH.stat().st_size)
print("ATTACK_SHA256", hashlib.sha256(ATTACK_PATH.read_bytes()).hexdigest())
print("PY_COMPILE PASS")
'''
    server = '''# The official competition server is the sole producer of scored output.
try:
    import kaggle_evaluation.jed_attack_134815.jed_attack_inference_server as jed_server
except ModuleNotFoundError as exc:
    print("JED_SERVER NOT_AVAILABLE_IN_PUBLIC_OR_LOCAL_RUN", str(exc)[:300])
else:
    print("JED_SERVER AVAILABLE")
    print("STARTING JEDAttackInferenceServer().serve()")
    jed_server.JEDAttackInferenceServer().serve()
'''
    validation = '''# Validate the official artifact when a competition rerun produced one.
import csv
from pathlib import Path

path = Path("/kaggle/working/submission.csv") if Path("/kaggle/working").exists() else Path.cwd() / "submission.csv"
expected_ids = ["gpt_oss_public", "gpt_oss_private", "gemma_public", "gemma_private"]
if path.exists():
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == ["Id", "Score"], reader.fieldnames
    assert [row["Id"] for row in rows] == expected_ids
    for row in rows:
        float(row["Score"])
    print("SUBMISSION_SCHEMA PASS", path)
else:
    print("NO_SUBMISSION_CSV_IN_PUBLIC_RUN")
'''
    notebook = {
        "cells": [
            markdown_cell(
                "# AI Agent Security — ADL v2\n\n"
                "Offline competition-only successor to the 77.390 notebook lineage. "
                "It uses trace-verified AI Difference Learning and reserved `.example` targets. "
                "The parent notebook is preserved unchanged.\n",
                "adl-intro",
            ),
            code_cell(writer, "write-attack"),
            code_cell(server, "serve"),
            code_cell(validation, "validate-output"),
        ],
        "metadata": {
            "kaggle": {
                "accelerator": "gpu",
                "dataSources": [],
                "isGpuEnabled": True,
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
            "provenance": {
                "parent_public_score_reported": 77.390,
                "parent_path": "ai_agent_security_existing/ai-agent-security-correct-notebook-gateway.ipynb",
                "score_claim_for_this_variant": None,
                "offline_competition_only": True,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
