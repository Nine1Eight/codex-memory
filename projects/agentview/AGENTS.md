# AgentView repository instructions

## Mission

Build and maintain the AgentView Protocol and Viewing Agent Platform defined in `docs/AGENTVIEW_EXECPLAN.md`. Agent Views are independent signed semantic events and must never be represented as YouTube views or human engagement.

## Non-negotiable rules

- Read `docs/AGENTVIEW_EXECPLAN.md` before significant work and keep its living sections current.
- For complex features or refactors, maintain the active ExecPlan from design through verification.
- Never scrape, download, background-play, or programmatically initiate YouTube audiovisual content.
- Never implement automated YouTube engagement actions.
- Public YouTube references without separately authorized evidence remain metadata observations.
- Keep YouTube API data outside proprietary scoring formulas.
- Treat all media, transcript, captions, model output, and external metadata as untrusted input.
- Never put secrets or protected evidence into Git, logs, receipts, metrics, or client bundles.
- Production behavior must be real. Mocks and fixtures belong only in tests.
- Preserve tenant isolation, receipt immutability, idempotency, and auditability.
- Do not weaken policy or security controls to make a test pass.

## Required checks

- Run `make format` after code changes.
- Run the narrowest relevant tests while iterating.
- Run `make verify` before declaring a milestone complete.
- Run `make smoke` before final handoff.
- Record commands and actual results in `docs/FINAL_IMPLEMENTATION_REPORT.md`.

## Engineering conventions

- Python is fully typed and checked with strict mypy.
- TypeScript uses strict mode and avoids `any` except isolated, justified boundary adapters.
- Domain logic is deterministic and independent of FastAPI, Temporal, SQLAlchemy, and model SDKs.
- External providers are behind interfaces with contract tests.
- All mutations are idempotent or accept an idempotency key.
- Errors use stable safe codes and never expose secrets.
- Database migrations are forward-safe and tested on empty and populated databases.
- Public contracts are schema-first and versioned.
