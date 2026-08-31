from packages.identity import OIDCClaims, TenantAccessPolicy, authorize, validate_oidc_claims
from packages.persistence import Role


def test_oidc_claim_validation() -> None:
    assert validate_oidc_claims(OIDCClaims("iss", "sub", "user@example.com", "tenant"))


def test_rbac_rules() -> None:
    assert authorize(TenantAccessPolicy("tenant", Role.ADMIN), "source.create").value == "allow"
    assert authorize(TenantAccessPolicy("tenant", Role.VIEWER), "source.create").value == "deny"
    assert authorize(TenantAccessPolicy("tenant", Role.AUDITOR), "audit.read").value == "allow"
