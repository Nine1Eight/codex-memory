from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from packages.persistence import Role


class RBACDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class OIDCClaims:
    issuer: str
    subject: str
    email: str
    tenant_id: str


@dataclass(frozen=True)
class SessionContext:
    tenant_id: str
    principal_id: str
    role: Role


@dataclass(frozen=True)
class TenantAccessPolicy:
    tenant_id: str
    role: Role

    def can_manage_sources(self) -> bool:
        return self.role in {Role.OWNER, Role.ADMIN, Role.OPERATOR}

    def can_view_audit(self) -> bool:
        return self.role in {Role.OWNER, Role.ADMIN, Role.AUDITOR}


def validate_oidc_claims(claims: OIDCClaims) -> bool:
    return all([claims.issuer, claims.subject, claims.email, claims.tenant_id])


def authorize(policy: TenantAccessPolicy, action: str) -> RBACDecision:
    if action in {"source.create", "source.revision.create", "authority.grant.create"}:
        return RBACDecision.ALLOW if policy.can_manage_sources() else RBACDecision.DENY
    if action == "audit.read":
        return RBACDecision.ALLOW if policy.can_view_audit() else RBACDecision.DENY
    return RBACDecision.DENY
