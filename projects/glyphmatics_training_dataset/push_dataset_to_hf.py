import os
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi
except Exception:
    print("[FAIL] huggingface_hub is not installed.")
    print("Run: python -m pip install --user huggingface_hub")
    sys.exit(1)

BASE = Path.home() / "glyphmatics_training_dataset"
REPO_ID = os.environ.get("REPO_ID", "Nine1Eight/glyphmatics-complete-training-dataset")
PRIVATE = os.environ.get("PRIVATE", "false").lower() in {"1", "true", "yes", "y"}
TOKEN = os.environ.get("HF_TOKEN", "").strip()

required = [
    "README.md",
    "dataset_infos.json",
    "data/train.jsonl",
    "data/validation.jsonl",
    "data/test.jsonl",
    "data/ontology.jsonl",
    "data/safety.jsonl",
]

missing = [f for f in required if not (BASE / f).exists()]
if missing:
    print("[FAIL] Missing dataset files:")
    for f in missing:
        print(" -", f)
    sys.exit(1)

if not TOKEN.startswith("hf_"):
    print("[FAIL] HF_TOKEN missing or invalid. It must start with hf_.")
    sys.exit(1)

api = HfApi(token=TOKEN)

print("[INFO] Dataset repo:", REPO_ID)
print("[INFO] Private:", PRIVATE)

api.create_repo(
    repo_id=REPO_ID,
    repo_type="dataset",
    private=PRIVATE,
    exist_ok=True,
)

api.upload_folder(
    folder_path=str(BASE),
    repo_id=REPO_ID,
    repo_type="dataset",
    commit_message="Add GlyphMatics complete training dataset",
    ignore_patterns=[
        ".git/*",
        "__pycache__/*",
        "*.pyc",
        ".env",
        "venv/*",
        ".venv/*",
    ],
)

print("[OK] Dataset uploaded.")
print(f"[OPEN] https://huggingface.co/datasets/{REPO_ID}")
