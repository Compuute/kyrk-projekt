"""Port for translating text between languages.

In test/memory mode, uses a fake that prefixes with the target language tag.
In production, calls the Anthropic API for real translation.
"""
from __future__ import annotations

from typing import Protocol


class TranslationPort(Protocol):
    def translate(self, text: str, source_lang: str, target_lang: str) -> str: ...
