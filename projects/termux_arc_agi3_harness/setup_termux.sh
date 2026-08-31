#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
printf '\n[ARC3] Termux setup starting...\n'
pkg update -y
pkg install -y python git clang make rust python-numpy
python -m venv .venv --system-site-packages
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install "pydantic>=2,<3" "typing-extensions>=4.8"
python -m pip install -e .
mkdir -p artifacts/episodes artifacts/datasets artifacts/reasoning artifacts/checkpoints
printf '\n[ARC3] Setup complete. Activate with:\n  . .venv/bin/activate\n\nTest with:\n  arc3-harness list-games\n  arc3-harness train-until-won --offline --cached-manifest --max-episodes 1 --max-steps 20\n'
