from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from packages.persistence import ImmutableError, PermissionError, Role, TenantStore


def test_cross_tenant_isolation() -> None:
    store = TenantStore()
    tenant_a = store.create_tenant("a", "A")
    tenant_b = store.create_tenant("b", "B")
    principal = store.create_principal("iss", "sub", "user@example.com")
    store.add_membership(tenant_a.id, principal.id, Role.ADMIN)
    source = store.create_source(tenant_a.id, "alpha", "uploaded_media", actor=principal.id)
    store.create_revision(tenant_a.id, source.id, "sha", {}, 1000, actor=principal.id)
    with pytest.raises(PermissionError):
        store.get_source(tenant_b.id, source.id)


def test_immutable_source_update_rejected() -> None:
    store = TenantStore()
    tenant = store.create_tenant("t", "Tenant")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant.id, "alpha", "uploaded_media", actor=principal.id)
    with pytest.raises(ImmutableError):
        store.update_source_title(tenant.id, source.id, "new")


def test_expired_authority_blocks_processing() -> None:
    store = TenantStore()
    tenant = store.create_tenant("t", "Tenant")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant.id, "alpha", "uploaded_media", actor=principal.id)
    store.create_revision(tenant.id, source.id, "sha", {}, 1000, actor=principal.id)
    store.create_authority_grant(
        tenant.id,
        source.id,
        "owned_media",
        datetime.now(timezone.utc) - timedelta(days=2),
        datetime.now(timezone.utc) - timedelta(days=1),
        actor=principal.id,
    )
    with pytest.raises(PermissionError):
        store.require_processing_authority(tenant.id, source.id)


def test_bootstrap_progress_starts_locked_and_counts_exactly() -> None:
    store = TenantStore()
    tenant = store.create_tenant("t", "Tenant")

    assert store.bootstrap_progress(tenant.id, 2) == {"count": 0, "threshold": 2, "locked": True}


def test_qualified_view_is_counted_once_and_duplicates_do_not_increment() -> None:
    store = TenantStore()
    tenant = store.create_tenant("t", "Tenant")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant.id, "alpha", "uploaded_media", actor=principal.id)
    revision = store.create_revision(tenant.id, source.id, "sha-1", {}, 1000, actor=principal.id)

    assert store.record_bootstrap_view(
        tenant_id=tenant.id,
        source_fingerprint_sha256="sha-1",
        source_id=source.id,
        source_revision_id=revision.id,
        receipt_id="receipt-1",
        objective_type="comprehensive_summary",
        view_class="multimodal",
        qualified=True,
        actor=principal.id,
    )
    assert not store.record_bootstrap_view(
        tenant_id=tenant.id,
        source_fingerprint_sha256="sha-1",
        source_id=source.id,
        source_revision_id=revision.id,
        receipt_id="receipt-2",
        objective_type="claim_inventory",
        view_class="multimodal",
        qualified=True,
        actor=principal.id,
    )
    assert store.bootstrap_progress(tenant.id, 2) == {"count": 1, "threshold": 2, "locked": True}


def test_nonqualifying_attempts_do_not_count() -> None:
    store = TenantStore()
    tenant = store.create_tenant("t", "Tenant")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant.id, "alpha", "uploaded_media", actor=principal.id)
    revision = store.create_revision(tenant.id, source.id, "sha-1", {}, 1000, actor=principal.id)

    for index, (view_class, qualified) in enumerate(
        [
            ("multimodal", False),
            ("transcript", False),
            ("visual", False),
            ("metadata_observation", False),
        ],
        start=1,
    ):
        assert not store.record_bootstrap_view(
            tenant_id=tenant.id,
            source_fingerprint_sha256=f"sha-{index}",
            source_id=source.id,
            source_revision_id=revision.id,
            receipt_id=f"receipt-{index}",
            objective_type="comprehensive_summary",
            view_class=view_class,
            qualified=qualified,
            actor=principal.id,
        )
    assert store.bootstrap_progress(tenant.id, 2) == {"count": 0, "threshold": 2, "locked": True}


def test_unqualified_first_attempt_does_not_poison_fingerprint() -> None:
    store = TenantStore()
    tenant = store.create_tenant("t", "Tenant")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant.id, "alpha", "uploaded_media", actor=principal.id)
    revision = store.create_revision(tenant.id, source.id, "sha-1", {}, 1000, actor=principal.id)

    assert not store.record_bootstrap_view(
        tenant_id=tenant.id,
        source_fingerprint_sha256="sha-1",
        source_id=source.id,
        source_revision_id=revision.id,
        receipt_id="receipt-1",
        objective_type="comprehensive_summary",
        view_class="multimodal",
        qualified=False,
        actor=principal.id,
    )
    assert store.record_bootstrap_view(
        tenant_id=tenant.id,
        source_fingerprint_sha256="sha-1",
        source_id=source.id,
        source_revision_id=revision.id,
        receipt_id="receipt-2",
        objective_type="comprehensive_summary",
        view_class="multimodal",
        qualified=True,
        actor=principal.id,
    )
    assert store.bootstrap_progress(tenant.id, 2) == {"count": 1, "threshold": 2, "locked": True}


def test_second_distinct_source_unlocks_recommendations() -> None:
    store = TenantStore()
    tenant = store.create_tenant("t", "Tenant")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant.id, "alpha", "uploaded_media", actor=principal.id)
    revision = store.create_revision(tenant.id, source.id, "sha-1", {}, 1000, actor=principal.id)
    source2 = store.create_source(tenant.id, "beta", "uploaded_media", actor=principal.id)
    revision2 = store.create_revision(tenant.id, source2.id, "sha-2", {}, 1000, actor=principal.id)

    assert store.record_bootstrap_view(
        tenant_id=tenant.id,
        source_fingerprint_sha256="sha-1",
        source_id=source.id,
        source_revision_id=revision.id,
        receipt_id="receipt-1",
        objective_type="comprehensive_summary",
        view_class="multimodal",
        qualified=True,
        actor=principal.id,
    )
    assert store.record_bootstrap_view(
        tenant_id=tenant.id,
        source_fingerprint_sha256="sha-2",
        source_id=source2.id,
        source_revision_id=revision2.id,
        receipt_id="receipt-2",
        objective_type="comprehensive_summary",
        view_class="multimodal",
        qualified=True,
        actor=principal.id,
    )
    assert store.bootstrap_progress(tenant.id, 2) == {"count": 2, "threshold": 2, "locked": False}


def test_tenant_isolation_keeps_counts_separate(tmp_path: Path) -> None:
    db_path = tmp_path / "store.sqlite3"
    store = TenantStore(str(db_path))
    tenant_a = store.create_tenant("a", "A")
    tenant_b = store.create_tenant("b", "B")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant_a.id, "alpha", "uploaded_media", actor=principal.id)
    revision = store.create_revision(tenant_a.id, source.id, "sha-1", {}, 1000, actor=principal.id)
    store.record_bootstrap_view(
        tenant_id=tenant_a.id,
        source_fingerprint_sha256="sha-1",
        source_id=source.id,
        source_revision_id=revision.id,
        receipt_id="receipt-1",
        objective_type="comprehensive_summary",
        view_class="multimodal",
        qualified=True,
        actor=principal.id,
    )
    assert store.bootstrap_progress(tenant_a.id, 2) == {"count": 1, "threshold": 2, "locked": True}
    assert store.bootstrap_progress(tenant_b.id, 2) == {"count": 0, "threshold": 2, "locked": True}


def test_bootstrap_progress_persists_across_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "persist.sqlite3"
    store = TenantStore(str(db_path))
    tenant = store.create_tenant("t", "Tenant")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant.id, "alpha", "uploaded_media", actor=principal.id)
    revision = store.create_revision(tenant.id, source.id, "sha-1", {}, 1000, actor=principal.id)
    store.record_bootstrap_view(
        tenant_id=tenant.id,
        source_fingerprint_sha256="sha-1",
        source_id=source.id,
        source_revision_id=revision.id,
        receipt_id="receipt-1",
        objective_type="comprehensive_summary",
        view_class="multimodal",
        qualified=True,
        actor=principal.id,
    )
    reopened = TenantStore(str(db_path))
    assert reopened.bootstrap_progress(tenant.id, 2) == {"count": 1, "threshold": 2, "locked": True}


def test_concurrent_same_fingerprint_counts_once(tmp_path: Path) -> None:
    db_path = tmp_path / "concurrent.sqlite3"
    store = TenantStore(str(db_path))
    tenant = store.create_tenant("t", "Tenant")
    principal = store.create_principal("iss", "sub", "user@example.com")
    source = store.create_source(tenant.id, "alpha", "uploaded_media", actor=principal.id)
    revision = store.create_revision(tenant.id, source.id, "sha-1", {}, 1000, actor=principal.id)

    def attempt(receipt_id: str) -> bool:
        worker_store = TenantStore(str(db_path))
        return worker_store.record_bootstrap_view(
            tenant_id=tenant.id,
            source_fingerprint_sha256="sha-1",
            source_id=source.id,
            source_revision_id=revision.id,
            receipt_id=receipt_id,
            objective_type="comprehensive_summary",
            view_class="multimodal",
            qualified=True,
            actor=principal.id,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(attempt, [f"receipt-{index}" for index in range(16)]))

    assert sum(1 for value in results if value) == 1
    assert store.bootstrap_progress(tenant.id, 2) == {"count": 1, "threshold": 2, "locked": True}
