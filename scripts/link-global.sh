#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
codex_dir="${CODEX_HOME:-$HOME/.codex}"
target="$codex_dir/AGENTS.md"
source_file="$repo_root/AGENTS.md"

mkdir -p "$codex_dir"

if [[ -L "$target" ]] && [[ "$(readlink -f "$target")" == "$source_file" ]]; then
  echo "Codex global instructions already linked: $target"
  exit 0
fi

if [[ -e "$target" || -L "$target" ]]; then
  echo "Refusing to replace existing file: $target" >&2
  echo "Review and move it manually, then rerun this script." >&2
  exit 1
fi

ln -s "$source_file" "$target"
echo "Linked $target -> $source_file"

