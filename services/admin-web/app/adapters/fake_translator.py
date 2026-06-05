"""Fake translator for tests and local dev.

Prefixes the text with the target language tag, e.g. "[am] Hej" for
a translation from Swedish to Amharic.
"""
from __future__ import annotations


class FakeTranslator:
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        return f"[{target_lang}] {text}"
