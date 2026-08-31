#!/usr/bin/env bash
set -euo pipefail

# Borg AI Swarm Agency Launch Deploy
# Creates/pushes:
# - GitHub repository + GitHub Pages workflow
# - Hugging Face model repository containing borg-agent-seed.borg
# - Hugging Face Space for browser-based seed download

GITHUB_OWNER="${GITHUB_OWNER:-BlockChain-BailBonds}"
REPO_NAME="${REPO_NAME:-borg-ai-swarm-agency}"
HF_OWNER="${HF_OWNER:-Nine1Eight}"
HF_MODEL_REPO="${HF_MODEL_REPO:-borg-agent-seed}"
HF_SPACE_REPO="${HF_SPACE_REPO:-borg-agent-seed-download}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST="$ROOT/dist"
MODEL_STAGE="$ROOT/../huggingface_model_repo"
SPACE_STAGE="$ROOT/../huggingface_space"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need git
need python3
need gh

if ! command -v hf >/dev/null 2>&1; then
  echo "Missing hf CLI. Install one of these:" >&2
  echo "  python3 -m pip install -U huggingface_hub" >&2
  echo "  curl -LsSf https://hf.co/cli/install.sh | bash" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI not authenticated. Run: gh auth login" >&2
  exit 1
fi

if [ -z "${HF_TOKEN:-}" ]; then
  echo "HF_TOKEN is not set. Run:" >&2
  echo "  export HF_TOKEN='hf_...'" >&2
  exit 1
fi

echo "[1/7] Building local Python package + seed..."
python3 -m pip install -e "$ROOT"
mkdir -p "$DIST"
python3 "$ROOT/scripts/create_seed.py" --out "$DIST/borg-agent-seed.borg"
sha256sum "$DIST/borg-agent-seed.borg" > "$DIST/SHA256SUMS"

echo "[2/7] Copying seed into GitHub Pages site..."
cp "$DIST/borg-agent-seed.borg" "$ROOT/site/borg-agent-seed.borg"
cp "$DIST/SHA256SUMS" "$ROOT/site/SHA256SUMS"

echo "[3/7] Initializing git repository..."
cd "$ROOT"
git init
git add .
git commit -m "Initial Borg AI Swarm Agency seed runtime" || true
git branch -M main

echo "[4/7] Creating/pushing GitHub repository..."
if gh repo view "$GITHUB_OWNER/$REPO_NAME" >/dev/null 2>&1; then
  echo "Repository exists: $GITHUB_OWNER/$REPO_NAME"
  git remote remove origin 2>/dev/null || true
  git remote add origin "https://github.com/$GITHUB_OWNER/$REPO_NAME.git"
  git push -u origin main
else
  gh repo create "$GITHUB_OWNER/$REPO_NAME" \
    --public \
    --description "Borg AI Swarm Agency seed runtime, Pages site, and Hugging Face deployment scaffold" \
    --source "$ROOT" \
    --remote origin \
    --push
fi

echo "[5/7] Enabling GitHub Pages workflow mode..."
gh api -X POST "repos/$GITHUB_OWNER/$REPO_NAME/pages" -f build_type=workflow >/dev/null 2>&1 || \
gh api -X PUT "repos/$GITHUB_OWNER/$REPO_NAME/pages" -f build_type=workflow >/dev/null 2>&1 || \
echo "Could not auto-enable Pages. Enable Settings -> Pages -> Source: GitHub Actions."

echo "[6/7] Publishing Hugging Face model repo..."
mkdir -p "$MODEL_STAGE"
cp "$DIST/borg-agent-seed.borg" "$MODEL_STAGE/borg-agent-seed.borg"
cp "$DIST/SHA256SUMS" "$MODEL_STAGE/SHA256SUMS"

hf repos create "$HF_OWNER/$HF_MODEL_REPO" --repo-type model --exist-ok --token "$HF_TOKEN"
hf upload "$HF_OWNER/$HF_MODEL_REPO" "$MODEL_STAGE" . \
  --repo-type model \
  --token "$HF_TOKEN" \
  --commit-message "Publish Borg agent seed capsule"

echo "[7/7] Publishing Hugging Face Space..."
hf repos create "$HF_OWNER/$HF_SPACE_REPO" --repo-type space --space-sdk gradio --exist-ok --token "$HF_TOKEN"
hf upload "$HF_OWNER/$HF_SPACE_REPO" "$SPACE_STAGE" . \
  --repo-type space \
  --token "$HF_TOKEN" \
  --commit-message "Publish Borg seed download Space"

echo
echo "DONE"
echo "GitHub repo:      https://github.com/$GITHUB_OWNER/$REPO_NAME"
echo "GitHub Pages:    https://$GITHUB_OWNER.github.io/$REPO_NAME/"
echo "HF model repo:   https://huggingface.co/$HF_OWNER/$HF_MODEL_REPO"
echo "HF Space:        https://huggingface.co/spaces/$HF_OWNER/$HF_SPACE_REPO"
