# Operations

## Real PostgreSQL test harness

Use this workflow on a host with a running Docker daemon:

```sh
docker compose -f compose.yaml up -d postgres
docker compose -f compose.yaml exec -T postgres pg_isready -U agentview -d agentview
docker compose -f compose.yaml exec -T postgres psql -U agentview -d agentview -v ON_ERROR_STOP=1 -f /workspace/migrations/0001_initial.sql
docker compose -f compose.yaml down -v --remove-orphans
```

## Local SQLite runtime

Use this workflow on the current host:

```sh
make migrate
make dev
```

## Notes

- The repository environment used for Codex does not currently have a usable Docker daemon, so the harness is documented for an external host rather than executed here.
- The migration file is stored at `migrations/0001_initial.sql`.
