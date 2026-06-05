"""Tests for the content editor module."""
from __future__ import annotations

import json

import pytest

from app.adapters.fake_content_store import FakeContentStore
from app.adapters.fake_translator import FakeTranslator


# --------------------------------------------------------- FakeContentStore unit


class TestFakeContentStore:
    def test_load_returns_default(self):
        store = FakeContentStore()
        data = store.load()
        assert data["version"] == "2.0"
        assert "sv" in data["church"]["name"]
        assert "am" in data["church"]["name"]

    def test_save_and_load(self):
        store = FakeContentStore()
        data = store.load()
        data["church"]["name"]["sv"] = "Ny kyrka"
        store.save(data)
        reloaded = store.load()
        assert reloaded["church"]["name"]["sv"] == "Ny kyrka"

    def test_load_returns_deep_copy(self):
        store = FakeContentStore()
        data1 = store.load()
        data1["church"]["name"]["sv"] = "Mutated"
        data2 = store.load()
        assert data2["church"]["name"]["sv"] != "Mutated"


# --------------------------------------------------------- FakeTranslator unit


class TestFakeTranslator:
    def test_translate_prefixes(self):
        t = FakeTranslator()
        result = t.translate("Hej", "sv", "am")
        assert result == "[am] Hej"

    def test_translate_other_lang(self):
        t = FakeTranslator()
        result = t.translate("Hello", "en", "sv")
        assert result == "[sv] Hello"


# --------------------------------------------------------- Content editor routes


def test_content_editor_requires_auth(client):
    r = client.get("/content-editor")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_content_editor_renders(authed_client):
    r = authed_client.get("/content-editor")
    assert r.status_code == 200
    assert "Innehållsredigerare" in r.text
    assert "Svenska" in r.text
    assert "Amhariska" in r.text
    # Should show church name key
    assert "church.name" in r.text


def test_content_editor_renders_sv_and_am_columns(authed_client):
    r = authed_client.get("/content-editor")
    assert r.status_code == 200
    # Check that both Swedish and Amharic content appears
    assert "Sankt Johannes" in r.text
    assert "ቅዱስ ዮሐንስ" in r.text


def test_content_editor_save(authed_client, content_store):
    r = authed_client.post(
        "/content-editor/save",
        data={
            "sv::church.name": "Uppdaterad kyrka",
            "am::church.name": "ተሻሽሏል",
        },
    )
    assert r.status_code == 303
    assert "/content-editor" in r.headers["location"]
    assert "flash=" in r.headers["location"]

    data = content_store.load()
    assert data["church"]["name"]["sv"] == "Uppdaterad kyrka"
    assert data["church"]["name"]["am"] == "ተሻሽሏል"


def test_content_editor_save_requires_auth(client):
    r = client.post("/content-editor/save", data={"sv::church.name": "test"})
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_content_editor_translate(authed_client):
    r = authed_client.post(
        "/content-editor/translate",
        json={"text": "Gudstjänst", "target_lang": "am"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["translated"] == "[am] Gudstjänst"


def test_content_editor_translate_requires_auth(client):
    r = client.post(
        "/content-editor/translate",
        json={"text": "test", "target_lang": "am"},
    )
    assert r.status_code == 302


def test_content_add_activity_form_renders(authed_client):
    r = authed_client.get("/content-editor/add-activity")
    assert r.status_code == 200
    assert "Lägg till aktivitet" in r.text
    assert "Titel" in r.text
    assert "Datum" in r.text


def test_content_add_activity_form_requires_auth(client):
    r = client.get("/content-editor/add-activity")
    assert r.status_code == 302


def test_content_add_activity_appends(authed_client, content_store):
    original = content_store.load()
    original_count = len(original.get("upcoming", []))

    r = authed_client.post(
        "/content-editor/add-activity",
        data={
            "title_sv": "Ny aktivitet",
            "activity_date": "2025-07-01",
            "activity_time": "14:00",
            "description_sv": "En ny aktivitet",
        },
    )
    assert r.status_code == 303
    assert "/content-editor" in r.headers["location"]

    data = content_store.load()
    assert len(data["upcoming"]) == original_count + 1
    new_activity = data["upcoming"][-1]
    assert new_activity["title"]["sv"] == "Ny aktivitet"
    assert new_activity["title"]["am"] == "[am] Ny aktivitet"
    assert new_activity["date"] == "2025-07-01"
    assert new_activity["time"] == "14:00"
    assert new_activity["description"]["sv"] == "En ny aktivitet"
    assert new_activity["description"]["am"] == "[am] En ny aktivitet"


def test_content_add_activity_requires_auth(client):
    r = client.post(
        "/content-editor/add-activity",
        data={
            "title_sv": "Test",
            "activity_date": "2025-07-01",
            "activity_time": "14:00",
            "description_sv": "Test",
        },
    )
    assert r.status_code == 302


# --------------------------------------------------------- Navbar


def test_navbar_has_innehall_link(authed_client):
    r = authed_client.get("/")
    assert r.status_code == 200
    assert 'href="/content-editor"' in r.text
    assert "Innehåll" in r.text


# --------------------------------------------------------- Factory


def test_factory_produces_fake_content_store():
    from app.adapters.factory import make_content_store
    from app.adapters.fake_content_store import FakeContentStore

    store = make_content_store()
    assert isinstance(store, FakeContentStore)


def test_factory_produces_fake_translator():
    from app.adapters.factory import make_translator
    from app.adapters.fake_translator import FakeTranslator

    translator = make_translator()
    assert isinstance(translator, FakeTranslator)
