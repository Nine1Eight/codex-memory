# Codex Memory

Portable, reviewable context for continuing work with Codex across devices.

This repository stores durable facts, decisions, project pointers, and handoffs.
It deliberately does **not** store generated Codex memory, chat transcripts,
credentials, tokens, SSH keys, or other machine-local state.

## Layout

- `AGENTS.md` — instructions Codex loads automatically.
- `MEMORY.md` — stable facts and working preferences.
- `projects/INDEX.md` — repositories and how to resume them.
- `decisions/` — durable decision records.
- `handoffs/CURRENT.md` — the immediate continuation point.
- `scripts/link-global.sh` — safely exposes these instructions to every local
  Codex workspace.

## First device

```bash
cd ~/codex-memory
./scripts/link-global.sh
```

The script creates `~/.codex/AGENTS.md` as a symlink. It refuses to replace an
existing file.

## Another device

```bash
git clone <private-repository-url> ~/codex-memory
~/codex-memory/scripts/link-global.sh
```

Keep the remote repository private. Review every change before committing, and
never add secrets.

## Updating context

Keep `MEMORY.md` short and durable. Put temporary status in
`handoffs/CURRENT.md`; move important settled choices into `decisions/`.

