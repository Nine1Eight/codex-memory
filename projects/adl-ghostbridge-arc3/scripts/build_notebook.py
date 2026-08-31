from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kaggle" / "adl_ghostbridge_arc3.ipynb"
TARGET = ROOT / "kaggle" / "arc_agi_3_winning_agent.ipynb"


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"missing canonical notebook: {SOURCE}")

    notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
    release = copy.deepcopy(notebook)

    # Kaggle reruns should start from a clean execution state. Keep the source
    # notebook untouched and produce a deterministic release artifact.
    for cell in release.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["execution_count"] = None
            cell["outputs"] = []

    metadata = release.setdefault("metadata", {})
    metadata["title"] = "ARC-AGI-3 Competition Agent — Qwen3.8 + GhostBridge"
    metadata["release"] = {
        "artifact": TARGET.name,
        "source": SOURCE.name,
        "offline_kaggle_rerun": True,
        "score_claim": "3.57 control-lineage provenance; future score not guaranteed",
    }

    serialized = json.dumps(release, ensure_ascii=False, separators=(",", ":")) + "\n"
    TARGET.write_text(serialized, encoding="utf-8")
    print(TARGET)


if __name__ == "__main__":
    main()
