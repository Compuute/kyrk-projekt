import json
import logging
import os
from typing import Any
import httpx
from app.ports.content_store import ContentStorePort

logger = logging.getLogger("admin-web.cloudflare_kv")


class CloudflareKVContentStore:
    """Production ContentStore adapter that reads and writes content to Cloudflare KV.

    Falls back to fake_content_store's DEFAULT_CONTENT if Cloudflare is unreachable
    or credentials are not configured.
    """

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        namespace_id: str | None = None,
        church_id: str | None = None,
    ) -> None:
        self._account_id = account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        self._api_token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self._namespace_id = namespace_id or os.environ.get("CLOUDFLARE_KV_NAMESPACE_ID", "")
        self._church_id = church_id or os.environ.get("CHURCH_ID", "nacka")
        self._fallback_data: dict | None = None

    def load(self) -> dict:
        if not all([self._account_id, self._api_token, self._namespace_id]):
            logger.warning("Cloudflare KV credentials missing, using local default")
            from app.adapters.fake_content_store import DEFAULT_CONTENT
            return DEFAULT_CONTENT

        url = f"https://api.cloudflare.com/client/v4/accounts/{self._account_id}/storage/kv/namespaces/{self._namespace_id}/values/{self._church_id}"
        headers = {"Authorization": f"Bearer {self._api_token}"}
        try:
            r = httpx.get(url, headers=headers, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                self._fallback_data = data
                return data
            elif r.status_code == 404:
                # Key doesn't exist yet, return default
                logger.info("Key %s not found in KV, using default content", self._church_id)
                from app.adapters.fake_content_store import DEFAULT_CONTENT
                return DEFAULT_CONTENT
            else:
                logger.warning("Cloudflare KV load failed with status %d: %s", r.status_code, r.text)
        except Exception as exc:
            logger.warning("Failed to fetch from Cloudflare KV: %s, using local fallback", exc)
        
        if self._fallback_data:
            return self._fallback_data
        from app.adapters.fake_content_store import DEFAULT_CONTENT
        return DEFAULT_CONTENT

    def save(self, content: dict) -> None:
        self._fallback_data = content
        if not all([self._account_id, self._api_token, self._namespace_id]):
            logger.warning("Cloudflare KV credentials missing, save skipped (local only)")
            return

        url = f"https://api.cloudflare.com/client/v4/accounts/{self._account_id}/storage/kv/namespaces/{self._namespace_id}/values/{self._church_id}"
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json"
        }
        try:
            r = httpx.put(url, headers=headers, content=json.dumps(content), timeout=5.0)
            if r.status_code != 200:
                logger.error("Cloudflare KV save failed: status=%d body=%s", r.status_code, r.text)
            else:
                logger.info("Successfully saved configuration for %s to Cloudflare KV", self._church_id)
        except Exception as exc:
            logger.error("Failed to write to Cloudflare KV: %s", exc)
