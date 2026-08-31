#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

mkdir -p docs spaces/player-ui-static federation schemas scripts

cat > README.md <<'README_EOF'
# HF Federated Game Competition Template

A GitHub template for building federated gaming competitions using multiple Hugging Face Spaces as connected service nodes.

## Live Gladiator AI Colosseum Spaces

Arena:
https://nine1eight-gladiator-ai-colosseum-arena.hf.space

Vault:
https://nine1eight-gladiator-ai-colosseum-vault.hf.space

Leaderboard:
https://nine1eight-gladiator-ai-colosseum-leaderboard.hf.space

## Core Pattern

GitHub is the blueprint.

Hugging Face Spaces are the running game network.

Each Space has one job:

| Space | Purpose |
|---|---|
| Landing Page | Promotion and play links |
| Arena | Runs matches |
| Vault | Stores agents, tools, games, submissions, and results |
| Leaderboard | Shows rankings |
| Player UI | Lets users build, submit, challenge, and agree |
| Agent Builder | Creates AI agents |
| Tool Builder | Creates tools and powers |
| Submission Gateway | Accepts bugs, games, agents, tools, and challenges |

## Minimum Health API

Every Space should expose:

```text
GET /api/health
