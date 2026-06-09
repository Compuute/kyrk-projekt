"""Webhook-based notification adapter (Zapier, custom webhooks, or any HTTP endpoint)."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("admin-web.notification")


class WebhookNotification:
    def __init__(self, webhook_url: str | None = None) -> None:
        self._url = (
            webhook_url 
            or os.environ.get("FUNERAL_CASE_WEBHOOK_URL") 
            or os.environ.get("N8N_WEBHOOK_FUNERAL_CASE", "")
        )

    def notify_new_funeral_case(self, payload: dict) -> None:
        if not self._url:
            logger.info("Webhook URL not configured, skipping")
            return
        try:
            import httpx
            httpx.post(self._url, json=payload, timeout=5.0)
        except Exception as exc:
            logger.warning("Webhook dispatch failed: %s", exc)
