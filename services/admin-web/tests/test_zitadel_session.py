import ssl

import pytest
from unittest.mock import MagicMock, patch

from app.adapters.jwt_session import JWTSessionAdapter


def test_jwks_client_verifies_tls():
    """Regression: the production JWKS fetch must verify TLS.

    JWTSessionAdapter runs only in ADAPTER_MODE=production (factory wires
    FakeSessionAdapter otherwise), and the JWKS fetch is the trust anchor for
    every admin session. Disabling certificate/hostname verification would let
    a MITM on the issuer connection serve forged signing keys and bypass admin
    authentication entirely.
    """
    adapter = JWTSessionAdapter("https://auth.example", "client")
    client = adapter._get_jwks_client()
    ctx = client.ssl_context
    # None => PyJWKClient/urllib uses the secure system default (verifies). OK.
    # A custom context is only acceptable if it still verifies cert + hostname.
    if ctx is not None:
        assert ctx.verify_mode == ssl.CERT_REQUIRED, "JWKS fetch must verify TLS certs"
        assert ctx.check_hostname is True, "JWKS fetch must verify the hostname"


def test_validate_missing_cookie():
    adapter = JWTSessionAdapter("https://auth.example", "client")
    assert adapter.validate(None) is None
    assert adapter.validate("") is None


@patch("jwt.PyJWKClient")
@patch("jwt.decode")
def test_validate_valid_cookie(mock_decode, mock_jwk_client_cls):
    mock_jwk_client = MagicMock()
    mock_jwk_client_cls.return_value = mock_jwk_client
    
    mock_signing_key = MagicMock()
    mock_signing_key.key = "public_key"
    mock_jwk_client.get_signing_key_from_jwt.return_value = mock_signing_key

    mock_decode.return_value = {
        "sub": "u-admin",
        "urn:zitadel:iam:org:id": "c-1",
        "urn:zitadel:iam:org:project:roles": {
            "admin": {
                "proj-1": ["c-1"]
            }
        }
    }

    adapter = JWTSessionAdapter("https://auth.example", "client")
    session = adapter.validate("valid.session.cookie")

    assert session is not None
    assert session.user_id == "u-admin"
    assert session.church_id == "c-1"
    assert session.role == "admin"


@patch("jwt.PyJWKClient")
@patch("jwt.decode")
def test_validate_invalid_cookie(mock_decode, mock_jwk_client_cls):
    mock_jwk_client = MagicMock()
    mock_jwk_client_cls.return_value = mock_jwk_client
    
    mock_signing_key = MagicMock()
    mock_signing_key.key = "public_key"
    mock_jwk_client.get_signing_key_from_jwt.return_value = mock_signing_key

    mock_decode.side_effect = Exception("invalid signature")

    adapter = JWTSessionAdapter("https://auth.example", "client")
    assert adapter.validate("invalid.cookie") is None


@patch("httpx.post")
def test_exchange_code_success(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"id_token": "my_id_token"}
    mock_post.return_value = mock_response

    adapter = JWTSessionAdapter(
        issuer_url="https://auth.example",
        client_id="client",
        client_secret="secret",
        redirect_uri="https://app.example/callback",
    )
    token = adapter.exchange_code("code123")
    assert token == "my_id_token"

    mock_post.assert_called_once_with(
        "https://auth.example/oauth/v2/token",
        data={
            "grant_type": "authorization_code",
            "code": "code123",
            "redirect_uri": "https://app.example/callback",
            "client_id": "client",
            "client_secret": "secret",
        },
        timeout=10.0,
    )
