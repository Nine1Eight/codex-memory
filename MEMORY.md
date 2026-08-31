# Durable Memory

Last reviewed: 2026-08-31

## Environment

- Primary local environment is Ubuntu 26.04 on x86-64.
- The development baseline includes Git, GitHub CLI, GCC, CMake, Ninja,
  Python 3.14 with pip/venv/pipx, Node.js 22 with npm/Corepack/pnpm/Yarn,
  ripgrep, fd, jq, ShellCheck, SQLite, and Gitleaks.
- GitHub CLI is authenticated as `Nine1Eight`, and Git uses its credential
  helper for GitHub HTTPS remotes.

## Current continuity facts

- This is a new device.
- The prior project checkout and its remote URL have not yet been recovered.
- The portable memory repository is private at
  `https://github.com/Nine1Eight/codex-memory`.

## Security baseline

- On 2026-08-31, Gitleaks scanned the complete Git history of all nine
  repositories under the `Nine1Eight` namespace.
- The scan covered seven public repositories, two private repositories, and
  three forks; it completed with zero findings and zero scan errors.
- Repository scans cover Git content and history, not GitHub issues, account
  settings, encrypted Actions secrets, or external systems.

## Working preferences

- Keep durable context in checked-in documentation rather than depending only
  on machine-local Codex memories.
- Keep secrets and generated Codex session state out of version control.
