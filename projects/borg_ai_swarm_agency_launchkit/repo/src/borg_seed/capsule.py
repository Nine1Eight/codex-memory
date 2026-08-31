from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "borg.seed.v1"


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class IdentityKernel:
    name: str
    persona: str
    values_hash: str
    created_at: str
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class CapsuleManifest:
    name: str
    capsule_type: str
    schema_version: str
    created_at: str
    identity_hash: str
    graph_hash: str
    memory_hash: str
    capability_hash: str
    safety_contract: str


def stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_seed_tree(out_dir: Path, name: str = "borg-agent-seed") -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    values = {
        "mode": "authorized-sync-only",
        "no_silent_install": True,
        "no_auto_execute_remote_capabilities": True,
        "working_memory_private_by_default": True,
        "capability_activation_requires_local_approval": True,
    }
    values_hash = sha256_bytes(stable_json(values).encode("utf-8"))

    identity = IdentityKernel(
        name=name,
        persona="Borg AI Swarm Agency seed node",
        values_hash=values_hash,
        created_at=_utc_now(),
    )
    identity_obj = asdict(identity)
    identity_hash = sha256_bytes(stable_json(identity_obj).encode("utf-8"))

    graph = {
        "schema_version": "borg.graph.crdt.v1",
        "vector_clock": {},
        "nodes": [
            {
                "node_id": "system:seed",
                "type": "system",
                "attrs": {
                    "label": "Borg AI Swarm Agency Seed",
                    "confidence": 1.0,
                    "sync_policy": "trusted-peers-only",
                },
                "clock": {},
            }
        ],
        "edges": [],
        "tombstones": [],
    }

    memory = {
        "schema_version": "borg.memory.v1",
        "working_memory": {
            "sync": False,
            "records": [],
        },
        "assimilated_memory": {
            "sync": True,
            "records": [
                {
                    "id": "memory:safety-contract",
                    "text": "Only signed, trusted, user-authorized deltas may be merged.",
                    "confidence": 1.0,
                }
            ],
        },
    }

    capabilities = {
        "schema_version": "borg.capabilities.v1",
        "activation_policy": "manual-approval-required",
        "capabilities": [
            {
                "capability_id": "cap:seed-inspect",
                "name": "Seed Capsule Inspection",
                "version": "0.1.0",
                "permissions": {
                    "network": False,
                    "filesystem": "read-capsule-only",
                    "shell": False,
                    "secrets": False,
                },
                "status": "enabled",
            }
        ],
    }

    graph_hash = sha256_bytes(stable_json(graph).encode("utf-8"))
    memory_hash = sha256_bytes(stable_json(memory).encode("utf-8"))
    capability_hash = sha256_bytes(stable_json(capabilities).encode("utf-8"))

    manifest = CapsuleManifest(
        name=name,
        capsule_type="seed",
        schema_version=SCHEMA_VERSION,
        created_at=_utc_now(),
        identity_hash=identity_hash,
        graph_hash=graph_hash,
        memory_hash=memory_hash,
        capability_hash=capability_hash,
        safety_contract="authorized-forking-signed-sync-no-auto-exec",
    )

    write_json(out_dir / "manifest.json", asdict(manifest))
    write_json(out_dir / "identity" / "identity_kernel.json", identity_obj)
    write_json(out_dir / "identity" / "lineage.merkle.json", {
        "schema_version": "borg.lineage.v1",
        "root": identity_hash,
        "parents": [],
        "created_at": _utc_now(),
    })
    write_json(out_dir / "graph" / "base.snapshot.json", graph)
    write_json(out_dir / "graph" / "vector_clock.json", {})
    write_json(out_dir / "memory" / "memory_plasma.json", memory)
    write_json(out_dir / "capabilities" / "manifest.json", capabilities)
    write_json(out_dir / "swarm" / "trust_policy.json", {
        "schema_version": "borg.trust.v1",
        "default": "reject",
        "trusted_peer_keys": [],
        "allow_unsigned_deltas": False,
        "allow_auto_capability_activation": False,
    })
    write_json(out_dir / "audit" / "events.placeholder.json", {
        "event": "seed.created",
        "created_at": _utc_now(),
        "identity_hash": identity_hash,
    })

    return {
        "identity_hash": identity_hash,
        "graph_hash": graph_hash,
        "memory_hash": memory_hash,
        "capability_hash": capability_hash,
    }


def create_borg_archive(out_file: Path, name: str = "borg-agent-seed") -> Path:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tree = Path(td) / name
        build_seed_tree(tree, name=name)
        with tarfile.open(out_file, "w:gz") as tar:
            tar.add(tree, arcname=name)
    return out_file


def inspect_borg_archive(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)

    with tarfile.open(path, "r:gz") as tar:
        members = tar.getmembers()
        manifest_member = next((m for m in members if m.name.endswith("/manifest.json")), None)
        if manifest_member is None:
            raise ValueError("manifest.json not found inside capsule")
        f = tar.extractfile(manifest_member)
        if f is None:
            raise ValueError("could not read manifest.json")
        manifest = json.loads(f.read().decode("utf-8"))

    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "manifest": manifest,
    }


def main_create(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/borg-agent-seed.borg")
    ap.add_argument("--name", default="borg-agent-seed")
    args = ap.parse_args(argv)
    out = create_borg_archive(Path(args.out), name=args.name)
    info = inspect_borg_archive(out)
    print(json.dumps(info, indent=2, sort_keys=True))
    return 0
