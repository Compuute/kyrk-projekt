"""Cloud KMS-backed field-level encryption.

Scope: one symmetric KMS key, encrypt/decrypt only. The service account
running this service needs `roles/cloudkms.cryptoKeyEncrypterDecrypter`
on that specific key — nothing wider.

Ciphertext is base64-encoded with a distinguishing prefix so operators
can tell at a glance that a value has been encrypted.

Exception paths never include the plaintext or ciphertext in error
messages.
"""
from __future__ import annotations

import base64
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.cloud.kms import KeyManagementServiceClient  # pragma: no cover


_PREFIX = "kms::"


class KmsEncryptionAdapter:
    def __init__(
        self,
        key_name: str,
        client: "KeyManagementServiceClient | None" = None,
    ) -> None:
        self._key_name = key_name
        self._client = client

    def _ensure_client(self):
        if self._client is None:
            # Lazy import so tests that never instantiate this adapter
            # don't require google-cloud-kms to be installed.
            from google.cloud import kms  # pragma: no cover

            self._client = kms.KeyManagementServiceClient()
        return self._client

    def encrypt(self, plaintext: str) -> str:
        client = self._ensure_client()
        response = client.encrypt(
            request={"name": self._key_name, "plaintext": plaintext.encode("utf-8")}
        )
        return _PREFIX + base64.b64encode(response.ciphertext).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext.startswith(_PREFIX):
            # Generic error — do not echo the ciphertext value.
            raise ValueError("not a KMS-encrypted value")
        raw = base64.b64decode(ciphertext[len(_PREFIX):].encode("ascii"))
        client = self._ensure_client()
        response = client.decrypt(request={"name": self._key_name, "ciphertext": raw})
        return response.plaintext.decode("utf-8")
