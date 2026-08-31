# Portable Codex context

## Session startup

- Read `$HOME/codex-memory/MEMORY.md` and
  `$HOME/codex-memory/handoffs/CURRENT.md` before substantial work when those
  files exist.
- Consult `$HOME/codex-memory/projects/INDEX.md` when locating or resuming a
  project.
- Treat repository-local `AGENTS.md` files as the authority for their scoped
  projects when they provide more specific instructions.

## Memory maintenance

- Store only durable, user-approved facts and preferences in `MEMORY.md`.
- Record the current continuation point in `handoffs/CURRENT.md` after
  substantial work in this repository.
- Record settled, consequential choices in `decisions/` with context and
  rationale.
- Distinguish verified facts from assumptions and remove stale context.
- Keep entries concise enough to review quickly.

## Safety

- Never store passwords, access tokens, API keys, private keys, credential
  files, raw chat transcripts, or the contents of `~/.codex/auth.json`.
- Do not copy generated files from `~/.codex/memories/` or
  `~/.codex/sessions/` into this repository.
- Keep any remote for this repository private.
- Do not commit or push unless the user requests it.

