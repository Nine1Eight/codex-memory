# Termux ARC-AGI-3 Public 25-Game Training Harness

Offline local training harness for the ARC-AGI-3 public 25 games. It vendors the pure-Python `arcengine` runtime and the public `environment_files` package from the competition archive.

## Install on Termux

```bash
cd ~/downloads/termux_arc_agi3_harness
chmod +x setup_termux.sh
./setup_termux.sh
. .venv/bin/activate
```

## List games

```bash
arc3-harness list-games
```

## Run bounded training

```bash
arc3-harness --offline --cached-manifest train-until-won --max-episodes 25 --checkpoint-every 1
```

## Run with gated known-sequence archive

Known sequences are diagnostic. They are gated and should not be blindly used for Kaggle submissions.

```bash
arc3-harness --offline --cached-manifest --use-known-sequences train-until-won --max-episodes 25 --checkpoint-every 1
```

## Check outputs

```bash
cat artifacts/autonomous_status.json
cat artifacts/summary.json
ls artifacts/episodes
ls artifacts/datasets
cat artifacts/reasoning/arc_agi3_reasoning_report.md
```

## Output files

- `artifacts/episodes/*.jsonl` — every action and transition
- `artifacts/datasets/arc_agi3_training.jsonl` — training rows
- `artifacts/reasoning/arc_agi3_reasoning_report.md` — run report
- `artifacts/checkpoints/*.json` — checkpoint state
- `artifacts/summary.json` — aggregate score summary

## Policy stack

1. Optional gated known sequence archive
2. Current-run state/action memory
3. BlindSight object/color heuristic
4. Vote/learn action value
5. Repeat/no-change guard
6. Low-risk fallback
