from pathlib import Path
from huggingface_hub import HfApi, upload_folder
import os

OWNER = os.environ.get("HF_USERNAME", "Nine1Eight")
TOKEN = os.environ.get("HF_TOKEN") or Path.home().joinpath(".cache/huggingface/token").read_text().strip()

spaces = [
    "gladiator-ai-colosseum-arena",
    "gladiator-ai-colosseum-vault",
    "gladiator-ai-colosseum-leaderboard",
]

root = Path("hf_multi_space_build")
api = HfApi(token=TOKEN)

for name in spaces:
    folder = root / name
    app_path = folder / "app.py"

    if not app_path.exists():
        print("MISSING:", app_path)
        continue

    s = app_path.read_text()

    s = s.replace(
        'Arena: {URLS.get("arena","")}\nVault: {URLS.get("vault","")}\nLeaderboard: {URLS.get("leaderboard","")}',
        'Arena: {arena_url}\nVault: {vault_url}\nLeaderboard: {leaderboard_url}'
    )

    s = s.replace(
        '<pre>Arena: {URLS.get("arena","")}\nVault: {URLS.get("vault","")}\nLeaderboard: {URLS.get("leaderboard","")}</pre>',
        '<pre>Arena: {arena_url}\nVault: {vault_url}\nLeaderboard: {leaderboard_url}</pre>'
    )

    app_path.write_text(s)

    repo_id = f"{OWNER}/{name}"
    print("Uploading fixed app:", repo_id)

    upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=str(folder),
        token=TOKEN,
    )

print("DONE: root page 500 patch uploaded.")
