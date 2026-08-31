# AgentView Protocol and Viewing Agent Platform

This repository is implementing the specification from the downloaded exec plan.

## Progress

- 2026-08-14: Milestone 0 started. Repository scaffolded, root instructions added, and a truthful setup-required API surface created.
- 2026-08-14: `make verify` passed on the bootstrap scaffold using local repository checks and the setup-status test.
- 2026-08-14: Milestone 1 in progress. Added the initial protocol package for canonical JSON, deduplication keys, Merkle roots, coverage, qualification math, and a local signer.
- 2026-08-14: Focused protocol tests passed: 7/7.
- 2026-08-14: Milestone 2 in progress. Added a tenant-scoped persistence layer with immutable sources, revisions, authority grants, and append-only audit events.
- 2026-08-14: Cross-tenant, immutability, authority-expiry, and audit-scoping tests passed: 11/11 combined with milestone 1 tests.
- 2026-08-14: Milestone 2 expanded with OIDC claim validation, RBAC checks, encrypted token protection, signing-key provider primitives, and an initial PostgreSQL migration file.
- 2026-08-14: Combined identity/security/persistence/protocol tests passed: 14/14.
- 2026-08-14: Added an app factory, explicit runtime config, and GitHub Actions CI skeleton for push/PR verification.
- 2026-08-14: Added a repeatable local migration runner and idempotent bootstrap context for the SQLite-backed runtime.
- 2026-08-14: Focused runtime tests remained green after the migration/bootstrap hardening: 17/17.
- 2026-08-14: Added a real media-analysis path for uploaded animated media, evidence extraction, claim generation, and signed receipt output.
- 2026-08-14: Focused media-analysis and API tests passed: 19/19.

## Discoveries

- 2026-08-14: No preexisting `agentview` repository was present in the workspace root.
- 2026-08-14: The environment does not have `fastapi` installed, so the milestone-0 bootstrap avoids external Python dependencies.
- 2026-08-14: No third-party Ed25519 library is installed in the environment, so the current milestone uses a deterministic local signer implementation for core receipt tests.
- 2026-08-14: No PostgreSQL server or driver is installed in the environment, so persistence milestone proofs are being exercised through a tenant-aware in-process store plus migration scaffolding.
- 2026-08-14: The environment still lacks a live PostgreSQL service, so database-layer invariants are represented in schema/migration artifacts plus store-level tests rather than executed against a real server.

## Decision Log

- 2026-08-14: Bootstrap first with a truthful setup-required API before deeper protocol and worker implementation.
- 2026-08-14: Implement the protocol layer with stdlib-only primitives first so the repository can be verified in this environment before integrating provider-specific dependencies.
- 2026-08-14: Implement persistence invariants in a tenant-aware store first because the environment lacks a live PostgreSQL stack; preserve the schema/migration surface for later database-backed wiring.
- 2026-08-14: Add identity, RBAC, token protection, and migration artifacts within Milestone 2 so service-layer authority checks remain aligned with the persisted tenant model.

## Outcomes

- Milestone 0 completed at the bootstrap level.
