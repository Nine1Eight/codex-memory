# ARC-AGI-3 Nine18 World-Model Build

This kit installs a custom ARC-AGI-3 agent into the official `arcprize/ARC-AGI-3-Agents` repository.

## What it adds

- `Nine18WorldModel` agent class
- Online transition memory per game in `nine18_memory/*.jsonl`
- Bounded UCB-style action selection
- Frame fingerprinting, histogram features, connected components, occupancy/bounding-box tracking
- Complex-action coordinate targeting from object centroids, changed cells, and low-discrepancy fallback points
- Local, online, and competition run scripts
- Memory summary tool

## Install

From this kit directory:

```bash
chmod +x install_arcagi3_nine18.sh configure_arc_key.sh run_local_ls20.sh run_online_one.sh run_competition_all.sh
./install_arcagi3_nine18.sh
```

The default repo path is:

```bash
~/arc3_api_run/ARC-AGI-3-Agents
```

To use a different path:

```bash
export ARC3_REPO_DIR="$HOME/ARC-AGI-3-Agents"
./install_arcagi3_nine18.sh
```

## Configure platform key

Get the key from `arcprize.org/platform`, then run:

```bash
./configure_arc_key.sh
```

The script asks for the key without echoing it and writes it to `.env` as `ARC_API_KEY`.

## Run local smoke test

```bash
./run_local_ls20.sh
```

To change game:

```bash
ARC3_GAME=wa30 ./run_local_ls20.sh
```

## Run one online scorecard game

```bash
./run_online_one.sh
```

## Run competition mode

```bash
./run_competition_all.sh
```

## Summarize learned transition memory

```bash
cd ~/arc3_api_run/ARC-AGI-3-Agents
python3 ../arcagi3_nine18_build/tools/summarize_nine18_memory.py nine18_memory
```

## Environment controls

```bash
export NINE18_MAX_ACTIONS=180
export NINE18_MEMORY_DIR=nine18_memory
export NINE18_DISABLE_MEMORY_LOG=0
```

`NINE18_MAX_ACTIONS` controls the agent's per-game action ceiling. Higher values explore more but can reduce action-efficiency score.

## Agent registration

The install script copies:

```bash
agents/nine18_world_model_agent.py
```

and patches:

```bash
agents/__init__.py
```

so the agent can be launched as:

```bash
uv run main.py --agent=nine18worldmodel --game=ls20
```
