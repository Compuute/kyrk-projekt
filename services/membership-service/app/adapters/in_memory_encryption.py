"""Trivial in-memory encryption adapter. NOT cryptographically secure.

Used only by tests and local dev. Production wires in a Cloud KMS adapter.
The interface is intentionally identical so a swap is one line.
"""
from __future__ import annotations

import base64


class InMemoryEncryptionAdapter:
    _PREFIX = "enc::"

    def encrypt(self, plaintext: str) -> str:
        return self._PREFIX + base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext.startswith(self._PREFIX):
            raise ValueError("not an encrypted value")
        return base64.b64decode(ciphertext[len(self._PREFIX):].encode("ascii")).decode("utf-8")
