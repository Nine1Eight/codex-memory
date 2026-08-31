import os
import sys
from pathlib import Path
from huggingface_hub import HfApi

repo_id = os.environ.get("REPO_ID", "Nine1Eight/sigilagi-glyphmatics-academic")
repo_type = os.environ.get("HF_REPO_TYPE", "space").strip().lower()
private = os.environ.get("PRIVATE", "false").strip().lower() in {"1", "true", "yes", "y"}
token = os.environ.get("HF_TOKEN", "").strip()

if repo_type not in {"space", "model", "dataset"}:
    print(f"[FAIL] Invalid HF_REPO_TYPE={repo_type}. Use: space, model, or dataset.")
    sys.exit(1)

if not token.startswith("hf_"):
    print("[FAIL] HF_TOKEN missing or invalid. It should start with hf_.")
    print("Set it with:")
    print("export HF_TOKEN='hf_your_token_here'")
    sys.exit(1)

required = ["README.md", "app.py", "requirements.txt"]
missing = [f for f in required if not Path(f).exists()]

if missing:
    print("[FAIL] Missing required files:", ", ".join(missing))
    print("Run Part 1 and Part 2 first.")
    sys.exit(1)

api = HfApi(token=token)

print(f"[INFO] Repo ID   : {repo_id}")
print(f"[INFO] Repo Type : {repo_type}")
print(f"[INFO] Private   : {private}")

try:
    if repo_type == "space":
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            private=private,
            exist_ok=True,
            space_sdk="gradio",
        )
    else:
        api.create_repo(
            repo_id=repo_id,
            repo_type=repo_type,
            private=private,
            exist_ok=True,
        )
except TypeError:
    api.create_repo(
        repo_id=repo_id,
        repo_type=repo_type,
        private=private,
        exist_ok=True,
    )

api.upload_folder(
    folder_path=".",
    repo_id=repo_id,
    repo_type=repo_type,
    commit_message="Add SigilAGI GlyphMatics academic write-up",
    ignore_patterns=[
        ".git/*",
        "__pycache__/*",
        "*.pyc",
        ".env",
        "venv/*",
        ".venv/*",
    ],
)

base = {
    "space": "https://huggingface.co/spaces",
    "model": "https://huggingface.co",
    "dataset": "https://huggingface.co/datasets",
}[repo_type]

print("[OK] Upload complete")
print(f"[OPEN] {base}/{repo_id}")
