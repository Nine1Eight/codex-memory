from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import hmac
import json
from typing import Protocol


@dataclass(frozen=True)
class EncryptedBlob:
    key_id: str
    nonce: str
    ciphertext: str
    tag: str


class KeyProvider(Protocol):
    def encrypt(self, plaintext: str, aad: str) -> EncryptedBlob: ...

    def decrypt(self, blob: EncryptedBlob, aad: str) -> str: ...


class SigningKeyProvider(Protocol):
    def public_key(self, key_id: str) -> str: ...


class LocalMasterKeyProvider:
    def __init__(self, key_id: str, master_key: bytes) -> None:
        self.key_id = key_id
        self.master_key = master_key

    def _mac(self, aad: str, payload: bytes) -> bytes:
        return hmac.new(self.master_key, aad.encode("utf-8") + b"\x1f" + payload, hashlib.sha256).digest()

    def encrypt(self, plaintext: str, aad: str) -> EncryptedBlob:
        payload = plaintext.encode("utf-8")
        nonce = hashlib.sha256(self.master_key + aad.encode("utf-8")).digest()[:12]
        mask = hashlib.sha256(self.master_key + nonce + aad.encode("utf-8")).digest()
        ciphertext = bytes(b ^ mask[i % len(mask)] for i, b in enumerate(payload))
        tag = self._mac(aad, nonce + ciphertext)
        return EncryptedBlob(
            key_id=self.key_id,
            nonce=base64.urlsafe_b64encode(nonce).rstrip(b"=").decode("ascii"),
            ciphertext=base64.urlsafe_b64encode(ciphertext).rstrip(b"=").decode("ascii"),
            tag=base64.urlsafe_b64encode(tag).rstrip(b"=").decode("ascii"),
        )

    def decrypt(self, blob: EncryptedBlob, aad: str) -> str:
        nonce = base64.urlsafe_b64decode(blob.nonce + "==")
        ciphertext = base64.urlsafe_b64decode(blob.ciphertext + "==")
        expected = base64.urlsafe_b64decode(blob.tag + "==")
        if not hmac.compare_digest(expected, self._mac(aad, nonce + ciphertext)):
            raise ValueError("authentication failed")
        mask = hashlib.sha256(self.master_key + nonce + aad.encode("utf-8")).digest()
        plaintext = bytes(b ^ mask[i % len(mask)] for i, b in enumerate(ciphertext))
        return plaintext.decode("utf-8")


class TokenProtector:
    def __init__(self, key_provider: KeyProvider, tenant_id: str) -> None:
        self.key_provider = key_provider
        self.tenant_id = tenant_id

    def protect(self, token_json: dict[str, str]) -> EncryptedBlob:
        return self.key_provider.encrypt(json.dumps(token_json, sort_keys=True), self.tenant_id)

    def unprotect(self, blob: EncryptedBlob) -> dict[str, str]:
        plaintext = self.key_provider.decrypt(blob, self.tenant_id)
        return json.loads(plaintext)
