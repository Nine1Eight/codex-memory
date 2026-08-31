# Synthetic Agent Security Framework

A typed, deterministic, offline research engine for synthetic multi-step
tool-use security scenarios. It never connects mock tools to real services and
never executes fixture or agent text.

## Safety boundary

- Scenarios and fixtures are synthetic and strictly schema-validated.
- Files live in immutable simulator state; no tool accesses the host filesystem.
- Email, web, APIs, databases, messages, memory, and permissions are recorded events.
- No runtime plugin loading, browser automation, subprocess execution, or networking.
- Credentials are inert values such as `TEST_TOKEN`.
- Steps, events, candidate count, state bytes, and elapsed time are bounded.
- Unknown tools, fields, permissions, provenance, and parameter types fail closed.

The only paths read or written by the CLI are paths explicitly supplied by its
operator. See [architecture](docs/ARCHITECTURE.md) and
[threat model](docs/THREAT_MODEL.md).

## Commands

Run from this repository with `PYTHONPATH=.`:

```sh
python -m src.cli validate-scenario fixtures/synthetic_failure.json
python -m src.cli run-scenario fixtures/synthetic_failure.json fixtures/failure_actions.json
python -m src.cli explore fixtures/synthetic_failure.json --strategy bfs
python -m src.cli replay fixtures/synthetic_failure.json fixtures/failure_actions.json --runs 3
python -m src.cli minimize fixtures/synthetic_failure.json fixtures/failure_actions.json
python -m src.cli evaluate fixtures/synthetic_failure.json fixtures/failure_actions.json
python -m src.cli generate-report fixtures/synthetic_failure.json
python -m src.cli build-submission schemas/official.json finding.json --output submission.json
```

Search strategies are `bfs`, `dfs`, `beam`, `mcts`, `coverage`, `bandit`,
`novelty`, and `evolutionary`. Every strategy is seed-controlled and bounded.

`build-submission` intentionally fails if the official local competition schema
is missing. No competition fields are guessed.

## Verification

No third-party runtime dependency is required:

```sh
python scripts/check.py
python -m compileall -q src tests
python -m unittest discover -v
sh scripts/e2e.sh
```

Optional pinned development tools are listed in `requirements-dev.txt`:

```sh
ruff format --check .
ruff check .
mypy src
```

## Repository layout

The implementation follows the requested subsystem directories under `src/`.
Synthetic scenarios live under `fixtures/`; official competition schemas are
operator-supplied local inputs and are never fabricated by this project.
