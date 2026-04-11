"""Field-level encryption port.

In production this wraps Cloud KMS. In tests, the in-memory adapter provides
deterministic round-tripping without a real key.
"""
from __future__ import annotations

from typing import Protocol


class EncryptionPort(Protocol):
    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, ciphertext: str) -> str: ...
