"""Anthropic-powered translator for production use.

Uses Claude to translate text with church-specific terminology guidance.
Lazy-imports the anthropic SDK to avoid requiring it at test time.
"""
from __future__ import annotations


class AnthropicTranslator:
    _SYSTEM_PROMPT = (
        "You are a translator for an Ethiopian Orthodox church. "
        "Translate the following text. "
        "Preserve the warm, inclusive tone. "
        "For church-specific terms use standard Ethiopian Orthodox Tewahedo terminology. "
        "Respond with ONLY the translated text, nothing else."
    )

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None  # lazy

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        client = self._get_client()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=self._SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Translate from {source_lang} to {target_lang}:\n\n{text}"
                    ),
                }
            ],
        )
        return message.content[0].text
