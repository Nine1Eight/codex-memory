#!/usr/bin/env bash
set -euo pipefail

OWNER="${HF_USERNAME:-Nine1Eight}"
TOKEN="${HF_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  if [ -s "$HOME/.cache/huggingface/token" ]; then
    TOKEN="$(cat "$HOME/.cache/huggingface/token")"
  else
    echo "ERROR: No HF_TOKEN and no ~/.cache/huggingface/token found"
    exit 1
  fi
fi

python - <<'PY'
import os
from pathlib import Path
from huggingface_hub import HfApi, upload_folder

owner = os.environ.get("HF_USERNAME", "Nine1Eight")
token = os.environ.get("HF_TOKEN") or Path.home().joinpath(".cache/huggingface/token").read_text().strip()
root = Path.cwd()

api = HfApi(token=token)

spaces = [
    {
        "name": "gladiator-ai-colosseum-arena",
        "role": "arena",
        "title": "Gladiator AI Colosseum — Arena Core",
        "description": "Primary playable arena, match router, and sandbox competition UI.",
    },
    {
        "name": "gladiator-ai-colosseum-vault",
        "role": "vault",
        "title": "Gladiator AI Colosseum — Vault",
        "description": "Trophy vault, match trace archive, and report export node.",
    },
    {
        "name": "gladiator-ai-colosseum-leaderboard",
        "role": "leaderboard",
        "title": "Gladiator AI Colosseum — Leaderboard",
        "description": "Federated leaderboard, player tracking, and cross-space score aggregation.",
    },
]

def space_url(space_name: str) -> str:
    return f"https://{owner.lower()}-{space_name.lower()}.hf.space"

all_urls = {s["role"]: space_url(s["name"]) for s in spaces}

ignore_patterns = [
    ".git/*",
    "__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    ".env",
    ".env.*",
    "data/*",
    "logs/*",
    "tmp/*",
    "node_modules/*",
    ".venv/*",
    "venv/*",
    "tok-venv/*",
    "vilenv/*",
    "scripts/deploy_multi_hf_spaces.sh",
]

for s in spaces:
    repo_id = f"{owner}/{s['name']}"
    role = s["role"]

    peer_urls = ",".join(
        url for peer_role, url in all_urls.items()
        if peer_role != role
    )

    print(f"\n=== Deploying {repo_id} [{role}] ===")

    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
        private=False,
    )

    # Runtime variables for federation.
    # If your installed huggingface_hub is older and lacks these methods,
    # deployment still continues; set variables manually in Space Settings.
    variables = {
        "SPACE_ROLE": role,
        "PUBLIC_SPACE_NAME": s["name"],
        "FEDERATION_PEERS": peer_urls,
        "ARENA_SPACE_URL": all_urls["arena"],
        "VAULT_SPACE_URL": all_urls["vault"],
        "LEADERBOARD_SPACE_URL": all_urls["leaderboard"],
        "APP_STORAGE_DIR": "/data",
    }

    for key, value in variables.items():
        try:
            api.add_space_variable(repo_id=repo_id, key=key, value=value)
            print(f"set variable {key}={value}")
        except Exception as e:
            print(f"warn: could not set variable {key}: {e}")

    try:
        api.add_space_secret(
            repo_id=repo_id,
            key="FEDERATION_TOKEN",
            value=os.environ.get("FEDERATION_TOKEN", "918-federation-local-dev-change-this"),
        )
        print("set secret FEDERATION_TOKEN")
    except Exception as e:
        print(f"warn: could not set secret FEDERATION_TOKEN: {e}")

    readme = root / "README.md"
    readme.write_text(
        f"""---
title: {s['title']}
emoji: ⚔️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# {s['title']}

{s['description']}

## Federation

- Arena: {all_urls['arena']}
- Vault: {all_urls['vault']}
- Leaderboard: {all_urls['leaderboard']}

## Runtime role

`SPACE_ROLE={role}`
""",
        encoding="utf-8",
    )

    upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=str(root),
        token=token,
        ignore_patterns=ignore_patterns,
    )

    print(f"deployed: https://huggingface.co/spaces/{repo_id}")
    print(f"runtime:  {space_url(s['name'])}")

print("\nMULTI-SPACE DEPLOY COMPLETE")
print(f"Arena:       {all_urls['arena']}")
print(f"Vault:       {all_urls['vault']}")
print(f"Leaderboard: {all_urls['leaderboard']}")
PY
