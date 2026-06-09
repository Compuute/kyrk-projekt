import pytest
import httpx
from app.adapters.factory import make_content_store
from app.adapters.cloudflare_kv_store import CloudflareKVContentStore
from app.adapters.fake_content_store import DEFAULT_CONTENT


class MockResponse:
    def __init__(self, json_data: dict, status_code: int, text: str = ""):
        self._json_data = json_data
        self.status_code = status_code
        self.text = text

    def json(self) -> dict:
        return self._json_data


def test_kv_store_falls_back_without_credentials():
    store = CloudflareKVContentStore(account_id="", api_token="", namespace_id="")
    assert store.load() == DEFAULT_CONTENT

    # Save should not raise exception
    store.save({"test": "value"})


def test_kv_store_load_success(monkeypatch):
    expected_data = {"version": "3.0", "church": {"name": {"sv": "Test KV", "am": "ተስት"}}}

    def mock_get(url, headers, timeout):
        assert "storage/kv/namespaces/ns123/values/nacka" in url
        assert headers["Authorization"] == "Bearer token123"
        return MockResponse(expected_data, 200)

    monkeypatch.setattr(httpx, "get", mock_get)

    store = CloudflareKVContentStore(
        account_id="acc123",
        api_token="token123",
        namespace_id="ns123",
        church_id="nacka"
    )
    data = store.load()
    assert data == expected_data
    assert store._fallback_data == expected_data


def test_kv_store_load_404(monkeypatch):
    def mock_get(url, headers, timeout):
        return MockResponse({}, 404)

    monkeypatch.setattr(httpx, "get", mock_get)

    store = CloudflareKVContentStore(
        account_id="acc123",
        api_token="token123",
        namespace_id="ns123",
        church_id="nacka"
    )
    data = store.load()
    assert data == DEFAULT_CONTENT


def test_kv_store_load_network_failure_falls_back_to_cache(monkeypatch):
    call_count = 0

    def mock_get(url, headers, timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockResponse({"test": "cached"}, 200)
        raise httpx.ConnectError("Connection failed")

    monkeypatch.setattr(httpx, "get", mock_get)

    store = CloudflareKVContentStore(
        account_id="acc123",
        api_token="token123",
        namespace_id="ns123",
        church_id="nacka"
    )
    # First load succeeds and caches fallback data
    data1 = store.load()
    assert data1 == {"test": "cached"}

    # Second load encounters network failure, falls back to cached data
    data2 = store.load()
    assert data2 == {"test": "cached"}


def test_kv_store_save_success(monkeypatch):
    payload = {"test": "save_payload"}
    put_called = False

    def mock_put(url, headers, content, timeout):
        nonlocal put_called
        put_called = True
        assert "storage/kv/namespaces/ns123/values/nacka" in url
        assert headers["Authorization"] == "Bearer token123"
        assert headers["Content-Type"] == "application/json"
        assert content == '{"test": "save_payload"}'
        return MockResponse({}, 200)

    monkeypatch.setattr(httpx, "put", mock_put)

    store = CloudflareKVContentStore(
        account_id="acc123",
        api_token="token123",
        namespace_id="ns123",
        church_id="nacka"
    )
    store.save(payload)
    assert put_called
    assert store._fallback_data == payload


def test_factory_resolves_cloudflare_kv_in_production(monkeypatch):
    monkeypatch.setenv("ADAPTER_MODE", "production")
    
    # Credentials are empty by default, but it should still instantiate the class
    store = make_content_store()
    assert isinstance(store, CloudflareKVContentStore)
