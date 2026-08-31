from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
import sqlite3
import threading
from typing import Any
import uuid


class ImmutableError(RuntimeError):
    pass


class PermissionError(RuntimeError):
    pass


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"
    AUDITOR = "auditor"


@dataclass(frozen=True)
class Tenant:
    id: str
    slug: str
    display_name: str


@dataclass(frozen=True)
class Principal:
    id: str
    oidc_issuer: str
    oidc_subject: str
    email_normalized: str


@dataclass(frozen=True)
class Source:
    id: str
    tenant_id: str
    title: str
    source_type: str
    current_revision_id: str | None = None


@dataclass(frozen=True)
class SourceRevision:
    id: str
    tenant_id: str
    source_id: str
    revision_number: int
    fingerprint_sha256: str
    duration_ms: int | None
    metadata: dict[str, Any]
    immutable: bool = True


@dataclass(frozen=True)
class AuthorityGrant:
    id: str
    tenant_id: str
    source_id: str
    authority_class: str
    status: str
    valid_from: datetime
    valid_until: datetime | None

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self.status != "active":
            return False
        return self.valid_from <= now and (self.valid_until is None or now <= self.valid_until)


@dataclass(frozen=True)
class AuditEvent:
    id: str
    tenant_id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    decision: str
    metadata: dict[str, Any]
    occurred_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


class TenantStore:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.RLock()
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tenants (
              id TEXT PRIMARY KEY,
              slug TEXT NOT NULL UNIQUE,
              display_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS principals (
              id TEXT PRIMARY KEY,
              oidc_issuer TEXT NOT NULL,
              oidc_subject TEXT NOT NULL,
              email_normalized TEXT NOT NULL,
              UNIQUE (oidc_issuer, oidc_subject)
            );
            CREATE TABLE IF NOT EXISTS memberships (
              tenant_id TEXT NOT NULL,
              principal_id TEXT NOT NULL,
              role TEXT NOT NULL,
              PRIMARY KEY (tenant_id, principal_id)
            );
            CREATE TABLE IF NOT EXISTS sources (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              title TEXT NOT NULL,
              source_type TEXT NOT NULL,
              current_revision_id TEXT
            );
            CREATE TABLE IF NOT EXISTS source_revisions (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              source_id TEXT NOT NULL,
              revision_number INTEGER NOT NULL,
              fingerprint_sha256 TEXT NOT NULL,
              duration_ms INTEGER,
              metadata_json TEXT NOT NULL,
              UNIQUE (source_id, revision_number),
              UNIQUE (source_id, fingerprint_sha256)
            );
            CREATE TABLE IF NOT EXISTS authority_grants (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              source_id TEXT NOT NULL,
              authority_class TEXT NOT NULL,
              status TEXT NOT NULL,
              valid_from TEXT NOT NULL,
              valid_until TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_events (
              id TEXT PRIMARY KEY,
              tenant_id TEXT NOT NULL,
              actor TEXT NOT NULL,
              action TEXT NOT NULL,
              resource_type TEXT NOT NULL,
              resource_id TEXT NOT NULL,
              decision TEXT NOT NULL,
              metadata_json TEXT NOT NULL,
              occurred_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bootstrap_views (
              tenant_id TEXT NOT NULL,
              source_fingerprint_sha256 TEXT NOT NULL,
              source_id TEXT NOT NULL,
              source_revision_id TEXT NOT NULL,
              receipt_id TEXT NOT NULL,
              objective_type TEXT NOT NULL,
              view_class TEXT NOT NULL,
              qualified INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY (tenant_id, source_fingerprint_sha256)
            );
            """
        )
        self._conn.commit()

    def create_tenant(self, slug: str, display_name: str) -> Tenant:
        tenant = Tenant(id=str(uuid.uuid4()), slug=slug, display_name=display_name)
        self._conn.execute(
            "INSERT INTO tenants (id, slug, display_name) VALUES (?, ?, ?)",
            (tenant.id, tenant.slug, tenant.display_name),
        )
        self._conn.commit()
        return tenant

    def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        row = self._conn.execute(
            "SELECT id, slug, display_name FROM tenants WHERE slug = ?",
            (slug,),
        ).fetchone()
        if row is None:
            return None
        return Tenant(id=row["id"], slug=row["slug"], display_name=row["display_name"])

    def create_principal(self, issuer: str, subject: str, email: str) -> Principal:
        principal = Principal(id=str(uuid.uuid4()), oidc_issuer=issuer, oidc_subject=subject, email_normalized=email)
        self._conn.execute(
            "INSERT INTO principals (id, oidc_issuer, oidc_subject, email_normalized) VALUES (?, ?, ?, ?)",
            (principal.id, principal.oidc_issuer, principal.oidc_subject, principal.email_normalized),
        )
        self._conn.commit()
        return principal

    def get_principal(self, issuer: str, subject: str) -> Principal | None:
        row = self._conn.execute(
            "SELECT id, oidc_issuer, oidc_subject, email_normalized FROM principals WHERE oidc_issuer = ? AND oidc_subject = ?",
            (issuer, subject),
        ).fetchone()
        if row is None:
            return None
        return Principal(id=row["id"], oidc_issuer=row["oidc_issuer"], oidc_subject=row["oidc_subject"], email_normalized=row["email_normalized"])

    def add_membership(self, tenant_id: str, principal_id: str, role: Role) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO memberships (tenant_id, principal_id, role) VALUES (?, ?, ?)",
            (tenant_id, principal_id, role.value),
        )
        self._conn.commit()

    def _assert_tenant(self, tenant_id: str, entity_tenant_id: str) -> None:
        if tenant_id != entity_tenant_id:
            raise PermissionError("cross-tenant access denied")

    def _record_audit(
        self,
        tenant_id: str,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        decision: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_events
            (id, tenant_id, actor, action, resource_type, resource_id, decision, metadata_json, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                tenant_id,
                actor,
                action,
                resource_type,
                resource_id,
                decision,
                json.dumps(metadata or {}, sort_keys=True),
                _to_iso(_now()),
            ),
        )
        self._conn.commit()

    def create_source(self, tenant_id: str, title: str, source_type: str, actor: str) -> Source:
        source = Source(id=str(uuid.uuid4()), tenant_id=tenant_id, title=title, source_type=source_type)
        self._conn.execute(
            "INSERT INTO sources (id, tenant_id, title, source_type) VALUES (?, ?, ?, ?)",
            (source.id, source.tenant_id, source.title, source.source_type),
        )
        self._conn.commit()
        self._record_audit(tenant_id, actor, "source.create", "source", source.id, "allow")
        return source

    def create_revision(
        self,
        tenant_id: str,
        source_id: str,
        fingerprint: str,
        metadata: dict[str, Any],
        duration_ms: int | None,
        actor: str,
    ) -> SourceRevision:
        source = self.get_source(tenant_id, source_id)
        next_revision = self._conn.execute(
            "SELECT COALESCE(MAX(revision_number), 0) + 1 AS next_revision FROM source_revisions WHERE source_id = ?",
            (source_id,),
        ).fetchone()["next_revision"]
        revision = SourceRevision(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            source_id=source_id,
            revision_number=int(next_revision),
            fingerprint_sha256=fingerprint,
            duration_ms=duration_ms,
            metadata=metadata,
        )
        self._conn.execute(
            """
            INSERT INTO source_revisions
            (id, tenant_id, source_id, revision_number, fingerprint_sha256, duration_ms, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision.id,
                revision.tenant_id,
                revision.source_id,
                revision.revision_number,
                revision.fingerprint_sha256,
                revision.duration_ms,
                json.dumps(metadata, sort_keys=True),
            ),
        )
        self._conn.execute("UPDATE sources SET current_revision_id = ? WHERE id = ?", (revision.id, source_id))
        self._conn.commit()
        self._record_audit(tenant_id, actor, "source.revision.create", "source_revision", revision.id, "allow")
        return revision

    def create_authority_grant(
        self,
        tenant_id: str,
        source_id: str,
        authority_class: str,
        valid_from: datetime,
        valid_until: datetime | None,
        actor: str,
    ) -> AuthorityGrant:
        source = self.get_source(tenant_id, source_id)
        grant = AuthorityGrant(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            source_id=source.id,
            authority_class=authority_class,
            status="active",
            valid_from=valid_from,
            valid_until=valid_until,
        )
        self._conn.execute(
            """
            INSERT INTO authority_grants
            (id, tenant_id, source_id, authority_class, status, valid_from, valid_until)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                grant.id,
                grant.tenant_id,
                grant.source_id,
                grant.authority_class,
                grant.status,
                _to_iso(grant.valid_from),
                _to_iso(grant.valid_until) if grant.valid_until else None,
            ),
        )
        self._conn.commit()
        self._record_audit(tenant_id, actor, "authority.grant.create", "authority_grant", grant.id, "allow")
        return grant

    def get_source(self, tenant_id: str, source_id: str) -> Source:
        row = self._conn.execute(
            "SELECT id, tenant_id, title, source_type, current_revision_id FROM sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            raise KeyError(source_id)
        self._assert_tenant(tenant_id, row["tenant_id"])
        return Source(
            id=row["id"],
            tenant_id=row["tenant_id"],
            title=row["title"],
            source_type=row["source_type"],
            current_revision_id=row["current_revision_id"],
        )

    def update_source_title(self, tenant_id: str, source_id: str, title: str) -> None:
        _ = self.get_source(tenant_id, source_id)
        raise ImmutableError("sources are immutable in this milestone; create a new revision")

    def find_active_grant(self, tenant_id: str, source_id: str, now: datetime | None = None) -> AuthorityGrant | None:
        now = now or _now()
        rows = self._conn.execute(
            """
            SELECT id, tenant_id, source_id, authority_class, status, valid_from, valid_until
            FROM authority_grants
            WHERE tenant_id = ? AND source_id = ?
            """,
            (tenant_id, source_id),
        ).fetchall()
        for row in rows:
            grant = AuthorityGrant(
                id=row["id"],
                tenant_id=row["tenant_id"],
                source_id=row["source_id"],
                authority_class=row["authority_class"],
                status=row["status"],
                valid_from=_from_iso(row["valid_from"]),
                valid_until=_from_iso(row["valid_until"]) if row["valid_until"] else None,
            )
            if grant.is_active(now):
                return grant
        return None

    def require_processing_authority(self, tenant_id: str, source_id: str, now: datetime | None = None) -> AuthorityGrant:
        source = self.get_source(tenant_id, source_id)
        grant = self.find_active_grant(tenant_id, source.id, now)
        if grant is None:
            raise PermissionError("expired or missing authority grant")
        return grant

    def audit_events(self, tenant_id: str) -> list[AuditEvent]:
        rows = self._conn.execute(
            """
            SELECT id, tenant_id, actor, action, resource_type, resource_id, decision, metadata_json, occurred_at
            FROM audit_events WHERE tenant_id = ? ORDER BY occurred_at ASC
            """,
            (tenant_id,),
        ).fetchall()
        return [
            AuditEvent(
                id=row["id"],
                tenant_id=row["tenant_id"],
                actor=row["actor"],
                action=row["action"],
                resource_type=row["resource_type"],
                resource_id=row["resource_id"],
                decision=row["decision"],
                metadata=json.loads(row["metadata_json"]),
                occurred_at=_from_iso(row["occurred_at"]),
            )
            for row in rows
        ]

    def record_bootstrap_view(
        self,
        *,
        tenant_id: str,
        source_fingerprint_sha256: str,
        source_id: str,
        source_revision_id: str,
        receipt_id: str,
        objective_type: str,
        view_class: str,
        qualified: bool,
        actor: str,
    ) -> bool:
        if not qualified or view_class != "multimodal":
            return False
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO bootstrap_views
                (tenant_id, source_fingerprint_sha256, source_id, source_revision_id, receipt_id, objective_type, view_class, qualified, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    source_fingerprint_sha256,
                    source_id,
                    source_revision_id,
                    receipt_id,
                    objective_type,
                    view_class,
                    1 if qualified else 0,
                    _to_iso(_now()),
                ),
            )
            inserted = cursor.rowcount == 1
            self._conn.commit()
        if inserted:
            self._record_audit(
                tenant_id,
                actor,
                "bootstrap.view.record",
                "bootstrap_view",
                source_fingerprint_sha256,
                "allow",
                {
                    "objective_type": objective_type,
                    "view_class": view_class,
                    "qualified": qualified,
                },
            )
        return inserted

    def bootstrap_progress(self, tenant_id: str, threshold: int) -> dict[str, int | bool]:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS count FROM bootstrap_views WHERE tenant_id = ? AND qualified = 1 AND view_class = 'multimodal'",
                (tenant_id,),
            ).fetchone()
        count = int(row["count"])
        return {"count": count, "threshold": threshold, "locked": count < threshold}
