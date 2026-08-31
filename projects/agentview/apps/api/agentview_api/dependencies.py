from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path

from packages.identity import OIDCClaims, TenantAccessPolicy, validate_oidc_claims
from packages.persistence import Role, TenantStore

from .config import load_config

store = TenantStore(load_config().database_path)
BOOTSTRAP_CONTEXT: RequestContext | None = None


@dataclass(frozen=True)
class RequestContext:
    tenant_id: str
    principal_id: str
    role: Role


def default_context() -> RequestContext:
    global BOOTSTRAP_CONTEXT
    if BOOTSTRAP_CONTEXT is not None:
        return BOOTSTRAP_CONTEXT
    tenant = store.get_tenant_by_slug("default") or store.create_tenant("default", "Default Tenant")
    principal = store.get_principal("https://issuer.example", "subject") or store.create_principal("https://issuer.example", "subject", "user@example.com")
    store.add_membership(tenant.id, principal.id, Role.ADMIN)
    claims = OIDCClaims("https://issuer.example", "subject", "user@example.com", tenant.id)
    if not validate_oidc_claims(claims):
        raise RuntimeError("invalid bootstrap claims")
    BOOTSTRAP_CONTEXT = RequestContext(tenant_id=tenant.id, principal_id=principal.id, role=Role.ADMIN)
    return BOOTSTRAP_CONTEXT


def policy_for(context: RequestContext) -> TenantAccessPolicy:
    return TenantAccessPolicy(context.tenant_id, context.role)
