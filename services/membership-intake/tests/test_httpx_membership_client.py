"""Serverless-auth header wiring for the membership-service forward."""
from __future__ import annotations

from app.adapters.httpx_membership_client import HttpxMembershipClient


def test_no_provider_means_no_serverless_header():
    c = HttpxMembershipClient(base_url="https://svc")
    assert c._serverless_headers() == {}


def test_provider_token_becomes_serverless_auth_header():
    c = HttpxMembershipClient(base_url="https://svc", id_token_provider=lambda aud: "idtok-" + aud[-3:])
    assert c._serverless_headers() == {"X-Serverless-Authorization": "Bearer idtok-svc"}


def test_provider_returning_none_adds_no_header():
    c = HttpxMembershipClient(base_url="https://svc", id_token_provider=lambda aud: None)
    assert c._serverless_headers() == {}
