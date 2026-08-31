# Glyphmatics Agent

This repository now contains:
- a 20,000-image sigil corpus split into shards
- an Agents SDK app that can inspect the corpus and summarize patterns

## Local Run

```bash
uv sync
uv run glyphmatics "Summarize the first shard and describe recurring shapes."
```

## Health Check

```bash
PORT=8000 uv run python main.py
curl -fsS http://127.0.0.1:8000/health
```

## Corpus Layout

- `shards/shard_02` through `shards/shard_07`
- `manifest.csv` in each shard
- symlinks point at the source PNGs in Android shared storage

## Notes

- `.env.local` is ignored and holds `OPENAI_API_KEY`
- the agent uses `gpt-4.1-mini`
