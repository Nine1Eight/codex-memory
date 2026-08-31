from packages.security import LocalMasterKeyProvider, TokenProtector


def test_token_encryption_round_trip() -> None:
    provider = LocalMasterKeyProvider("local", b"super-secret-master-key")
    protector = TokenProtector(provider, "tenant-a")
    blob = protector.protect({"refresh_token": "rt", "scope": "openid"})
    assert protector.unprotect(blob) == {"refresh_token": "rt", "scope": "openid"}
