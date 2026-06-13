"""Repo guard: admin-web's church list must match the canonical one.

The canonical church list is frontend/member-portal/churches.json. admin-web
carries a trimmed copy (id + name + city) for its certificate dropdown.
This guard fails if the two drift — edit the canonical file and resync the
copy, never patch one side.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "frontend" / "member-portal" / "churches.json"
ADMIN_COPY = ROOT / "services" / "admin-web" / "app" / "data" / "churches.json"


def _by_id(data):
    return {c["id"]: c for c in data["churches"]}


def test_admin_web_church_list_matches_canonical():
    canonical = _by_id(json.loads(CANONICAL.read_text(encoding="utf-8")))
    copy = _by_id(json.loads(ADMIN_COPY.read_text(encoding="utf-8")))

    assert set(copy) == set(canonical), (
        "admin-web churches.json has different church ids than the canonical "
        "frontend/member-portal/churches.json — resync the copy"
    )
    for cid, church in copy.items():
        src = canonical[cid]
        assert church["name"]["sv"] == src["name"]["sv"], f"{cid} sv name drifted"
        assert church["name"]["am"] == src["name"]["am"], f"{cid} am name drifted"
        assert church["city"] == src["city"], f"{cid} city drifted"
