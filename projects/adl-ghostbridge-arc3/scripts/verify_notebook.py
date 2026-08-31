from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK = ROOT / "kaggle" / "arc_agi_3_winning_agent.ipynb"

REQUIRED_TEXT = (
    "submission.parquet",
    "await bm.run(",
    "GHOSTBRIDGE_PREMOVE",
    "POST_MOVE_ADL",
    "OperationMode.COMPETITION",
    '"environment_passes_per_game": 1',
    "Qwen/Qwen3.8-27B-FP8",
    "KAGGLE_IS_COMPETITION_RERUN",
)
REQUIRED_COLUMNS = ("row_id", "game_id", "end_of_game", "score")
REQUIRED_SOURCE_TYPES = {
    "competition",
    "datasetVersion",
    "modelInstanceVersion",
}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)


def source_text(cell: dict) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else str(source)


def verify(path: Path) -> None:
    errors: list[str] = []
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"cannot read notebook {path}: {exc}") from exc

    if notebook.get("nbformat") != 4:
        errors.append("nbformat must be 4")
    cells = notebook.get("cells")
    if not isinstance(cells, list) or not cells:
        errors.append("notebook must contain cells")
        cells = []

    metadata = notebook.get("metadata", {})
    kaggle = metadata.get("kaggle", {})
    if kaggle.get("isInternetEnabled") is not False:
        errors.append("Kaggle internet must be disabled")
    if kaggle.get("isGpuEnabled") is not True:
        errors.append("Kaggle GPU must be enabled")
    source_types = {
        item.get("sourceType") for item in kaggle.get("dataSources", [])
        if isinstance(item, dict)
    }
    missing_types = REQUIRED_SOURCE_TYPES - source_types
    if missing_types:
        errors.append(f"missing Kaggle data source types: {sorted(missing_types)}")

    all_text = "\n".join(source_text(cell) for cell in cells)
    for marker in REQUIRED_TEXT:
        if marker not in all_text:
            errors.append(f"missing runtime contract marker: {marker}")
    for column in REQUIRED_COLUMNS:
        if f'"{column}"' not in all_text:
            errors.append(f"missing submission column: {column}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(all_text):
            errors.append(f"possible embedded secret matching {pattern.pattern}")

    run_position = all_text.find("await bm.run(")
    submission_position = all_text.find("SUBMISSION_PATH =")
    if run_position < 0 or submission_position <= run_position:
        errors.append("submission must be constructed after the scored run")

    for index, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs", []) != []:
            errors.append(f"code cell {index} contains outputs")
        if cell.get("execution_count") is not None:
            errors.append(f"code cell {index} has an execution count")
        try:
            compile(
                source_text(cell),
                f"{path.name}:cell-{index}",
                "exec",
                flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            )
        except SyntaxError as exc:
            errors.append(
                f"code cell {index} syntax error at line {exc.lineno}: {exc.msg}"
            )

    score_meta = metadata.get("score_optimization", {})
    if score_meta.get("environment_passes_per_game") != 1:
        errors.append("metadata must enforce one environment pass per game")
    if score_meta.get("qwen36_fallback") is not False:
        errors.append("Qwen3.6 fallback must remain disabled")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(f"NOTEBOOK_VERIFICATION_FAILED errors={len(errors)}")

    print(
        "NOTEBOOK_RELEASE_OK "
        f"path={path} cells={len(cells)} bytes={path.stat().st_size} "
        f"sources={sorted(source_types)} syntax=pass secrets=pass"
    )


if __name__ == "__main__":
    selected = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_NOTEBOOK
    verify(selected)
