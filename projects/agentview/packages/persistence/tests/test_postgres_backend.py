from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = ROOT / "compose.yaml"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, check=True, text=True, capture_output=True)


def _compose(*args: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker is required for the postgres integration test")
def test_postgres_migration_and_bootstrap_write_path() -> None:
    if shutil.which("docker") is None:
        pytest.skip("docker is required")

    try:
        try:
            _run(_compose("up", "-d", "postgres"))
        except subprocess.CalledProcessError as exc:
            pytest.skip(f"docker compose unavailable: {exc.stderr.strip() or exc.stdout.strip()}")
        for _ in range(60):
            ready = subprocess.run(
                _compose("exec", "-T", "postgres", "pg_isready", "-U", "agentview", "-d", "agentview"),
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            if ready.returncode == 0:
                break
        else:
            raise AssertionError("postgres did not become ready")

        _run(_compose("exec", "-T", "postgres", "psql", "-U", "agentview", "-d", "agentview", "-v", "ON_ERROR_STOP=1", "-f", "/workspace/migrations/0001_initial.sql"))

        table_exists = _run(
            _compose(
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "agentview",
                "-d",
                "agentview",
                "-tA",
                "-c",
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'bootstrap_views';",
            )
        )
        assert table_exists.stdout.strip() == "1"

        pk = _run(
            _compose(
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "agentview",
                "-d",
                "agentview",
                "-tA",
                "-c",
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'bootstrap_views'::regclass AND contype = 'p';
                """,
            )
        )
        assert "PRIMARY KEY (tenant_id, source_fingerprint_sha256)" in pk.stdout

        tenant_index = _run(
            _compose(
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "agentview",
                "-d",
                "agentview",
                "-tA",
                "-c",
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE tablename = 'bootstrap_views' AND indexname = 'idx_bootstrap_views_tenant';
                """,
            )
        )
        assert "CREATE INDEX idx_bootstrap_views_tenant" in tenant_index.stdout

        write_once = _run(
            _compose(
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "agentview",
                "-d",
                "agentview",
                "-v",
                "ON_ERROR_STOP=1",
                "-tA",
                "-c",
                """
                INSERT INTO bootstrap_views
                (tenant_id, source_fingerprint_sha256, source_id, source_revision_id, receipt_id, objective_type, view_class, qualified, created_at)
                VALUES
                ('tenant-a', 'sha-1', 'source-a', 'revision-a', 'receipt-a', 'comprehensive_summary', 'multimodal', 1, '2026-08-14T00:00:00Z');
                SELECT COUNT(*) FROM bootstrap_views WHERE tenant_id = 'tenant-a' AND qualified = 1 AND view_class = 'multimodal';
                """,
            )
        )
        assert write_once.stdout.strip().splitlines()[-1] == "1"

        duplicate = _run(
            _compose(
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "agentview",
                "-d",
                "agentview",
                "-v",
                "ON_ERROR_STOP=1",
                "-tA",
                "-c",
                """
                INSERT INTO bootstrap_views
                (tenant_id, source_fingerprint_sha256, source_id, source_revision_id, receipt_id, objective_type, view_class, qualified, created_at)
                VALUES
                ('tenant-a', 'sha-1', 'source-a', 'revision-b', 'receipt-b', 'claim_inventory', 'multimodal', 1, '2026-08-14T00:00:00Z')
                ON CONFLICT DO NOTHING;
                SELECT COUNT(*) FROM bootstrap_views WHERE tenant_id = 'tenant-a' AND qualified = 1 AND view_class = 'multimodal';
                """,
            )
        )
        assert duplicate.stdout.strip().splitlines()[-1] == "1"
    finally:
        subprocess.run(_compose("down", "-v", "--remove-orphans"), cwd=ROOT, text=True, capture_output=True)
