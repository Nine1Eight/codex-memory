#!/usr/bin/env python3
"""Build a provenance-preserving GlyphMatics VIL dataset from owned repos."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


TEXT_EXTENSIONS = {
    ".bash", ".c", ".cfg", ".cpp", ".css", ".csv", ".go", ".h", ".hpp",
    ".html", ".ini", ".ipynb", ".java", ".js", ".json", ".jsonl", ".jsx",
    ".kt", ".md", ".php", ".ps1", ".py", ".rb", ".rs", ".sh", ".sql",
    ".svg", ".toml", ".ts", ".tsx", ".txt", ".xml", ".yaml", ".yml",
}
SKIP_PARTS = {
    ".git", ".hg", ".svn", ".venv", "__pycache__", "build", "dist",
    "node_modules", "site-packages", "target", "vendor",
}
SENSITIVE_NAMES = re.compile(
    r"(^|/)(\.env($|\.)|id_(rsa|ed25519)|.*credentials?.*|.*secrets?.*|"
    r".*tokens?.*|hosts\.yml|cookies?\.txt)", re.IGNORECASE,
)
SENSITIVE_CONTENT = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password)\b"
        r"\s*[:=]\s*['\"](?!example|placeholder|changeme|test)[^'\"\s]{12,}['\"]"
    ),
]
LAYER_TERMS = {
    "AGENT": ("agent", "planner", "orchestrat", "tool_call"),
    "MODEL": ("model", "tensor", "inference", "embedding", "lora"),
    "DATA": ("dataset", "corpus", "jsonl", "loader", "ingest"),
    "VISUAL": ("vision", "visual", "image", "glyph", "canvas", "render"),
    "RUNTIME": ("runtime", "execute", "server", "cli", "pipeline"),
    "SECURITY": ("security", "hash", "sha256", "encrypt", "verify"),
    "EVAL": ("test", "benchmark", "score", "eval", "kaggle", "arc-agi"),
    "DOCS": ("readme", "documentation", ".md"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def layers_for(path: str, content: str) -> list[str]:
    sample = (path + "\n" + content[:20_000]).lower()
    layers = [name for name, terms in LAYER_TERMS.items() if any(term in sample for term in terms)]
    return layers or ["CODE"]


def glyph_sequence(layers: list[str], digest: str) -> list[str]:
    return ["OPEN", *layers[:6], f"HASH_{digest[:8].upper()}", "VALIDATE", "CLOSE"]


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if SENSITIVE_NAMES.search(relative):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS or path.name.upper().startswith(("README", "LICENSE")):
            yield path


def read_inventory(path: Path) -> list[dict[str, Any]]:
    repos = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        owner_repo, size_kb, private, fork, branch = line.split("\t")
        repos.append({
            "name_with_owner": owner_repo, "size_kb": int(size_kb or 0),
            "private": private == "true", "fork": fork == "true",
            "default_branch": branch,
        })
    return repos


def build(inventory_path: Path, checkout_root: Path, output: Path, max_file_bytes: int) -> dict[str, Any]:
    repos = read_inventory(inventory_path)
    output.mkdir(parents=True, exist_ok=True)
    handles = {
        split: gzip.open(output / f"{split}.jsonl.gz", "wt", encoding="utf-8")
        for split in ("train", "validation", "test")
    }
    seen: set[str] = set()
    counts = Counter()
    repo_counts = Counter()
    skipped = Counter()
    try:
        for repo in repos:
            owner_repo = repo["name_with_owner"]
            root = checkout_root / owner_repo.replace("/", "__")
            if not root.exists():
                root = checkout_root / owner_repo.replace("/", "_")
            if not root.exists():
                skipped["repository_unavailable"] += 1
                continue
            for path in iter_files(root):
                relative = path.relative_to(root).as_posix()
                size = path.stat().st_size
                if size > max_file_bytes:
                    skipped["file_too_large"] += 1
                    continue
                data = path.read_bytes()
                if b"\0" in data:
                    skipped["binary"] += 1
                    continue
                content = data.decode("utf-8", errors="replace")
                if any(pattern.search(content) for pattern in SENSITIVE_CONTENT):
                    skipped["sensitive_content"] += 1
                    continue
                digest = sha256(content.encode("utf-8"))
                if digest in seen:
                    skipped["duplicate_content"] += 1
                    continue
                seen.add(digest)
                layers = layers_for(relative, content)
                bucket = int(digest[:8], 16) % 100
                split = "train" if bucket < 90 else "validation" if bucket < 95 else "test"
                record = {
                    "id": f"repo-{digest[:24]}",
                    "version": "1.0.0",
                    "task_type": "repository_source_to_glyphmatic_vil",
                    "instruction": "Encode owned repository source into a provenance-preserving GlyphMatics VIL representation.",
                    "input": {"source_text": content},
                    "output": {
                        "canonical_construct": ">".join(glyph_sequence(layers, digest)),
                        "glyph_sequence": glyph_sequence(layers, digest),
                        "layers": layers,
                        "compressed_form": "|".join(layers + [digest[:16]]),
                        "source_sha256": digest,
                    },
                    "metadata": {
                        "source_repository": owner_repo, "source_path": relative,
                        "source_private": repo["private"], "source_fork": repo["fork"],
                        "default_branch": repo["default_branch"],
                        "author_namespace": owner_repo.split("/", 1)[0],
                        "organization": "918 Technologies",
                        "redistribution": "private" if repo["private"] else "owner_asserted",
                    },
                    "record_hash": sha256(f"{owner_repo}\0{relative}\0{digest}".encode()),
                }
                handles[split].write(json.dumps(record, ensure_ascii=False) + "\n")
                counts[split] += 1
                repo_counts[owner_repo] += 1
    finally:
        for handle in handles.values():
            handle.close()
    manifest = {
        "format": "GlyphMatics Owned Repository VIL Dataset",
        "version": "1.0.0",
        "repositories_declared": len(repos),
        "repositories_ingested": len(repo_counts),
        "records": dict(counts),
        "total_records": sum(counts.values()),
        "repository_records": dict(sorted(repo_counts.items())),
        "skipped": dict(skipped),
        "privacy": "Contains private-source records; keep private unless explicitly reviewed.",
        "inventory": repos,
    }
    manifest["manifest_sha256"] = sha256(json.dumps(manifest, sort_keys=True).encode())
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--checkout-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-file-bytes", type=int, default=500_000)
    args = parser.parse_args()
    print(json.dumps(build(args.inventory, args.checkout_root, args.output, args.max_file_bytes), indent=2))


if __name__ == "__main__":
    main()
