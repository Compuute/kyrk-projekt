import pytest
from unittest.mock import MagicMock, patch

from app.domain.errors import NotAuthorized
from app.domain.models import Role
from app.adapters.zitadel_auth import ZitadelAuthAdapter


def test_authenticate_missing_token():
    adapter = ZitadelAuthAdapter("https://auth.example", "client")
    with pytest.raises(NotAuthorized, match="missing token"):
        adapter.authenticate("")


@patch("jwt.PyJWKClient")
@patch("jwt.decode")
def test_authenticate_valid_token(mock_decode, mock_jwk_client_cls):
    mock_jwk_client = MagicMock()
    mock_jwk_client_cls.return_value = mock_jwk_client
    
    mock_signing_key = MagicMock()
    mock_signing_key.key = "public_key"
    mock_jwk_client.get_signing_key_from_jwt.return_value = mock_signing_key

    mock_decode.return_value = {
        "sub": "u-1",
        "urn:zitadel:iam:org:id": "c-1",
        "urn:zitadel:iam:org:project:roles": {
            "editor": {
                "proj-1": ["c-1"]
            }
        }
    }

    adapter = ZitadelAuthAdapter("https://auth.example", "client")
    actor = adapter.authenticate("some.jwt.token")

    assert actor.user_id == "u-1"
    assert actor.church_id == "c-1"
    assert actor.role == Role.EDITOR

    mock_jwk_client_cls.assert_called_once()
    assert mock_jwk_client_cls.call_args[0][0] == "https://auth.example/oauth/v2/keys"
    mock_jwk_client.get_signing_key_from_jwt.assert_called_once_with("some.jwt.token")


@patch("jwt.PyJWKClient")
@patch("jwt.decode")
def test_authenticate_invalid_claims(mock_decode, mock_jwk_client_cls):
    mock_jwk_client = MagicMock()
    mock_jwk_client_cls.return_value = mock_jwk_client
    
    mock_signing_key = MagicMock()
    mock_signing_key.key = "public_key"
    mock_jwk_client.get_signing_key_from_jwt.return_value = mock_signing_key

    mock_decode.return_value = {
        "sub": "u-1"
    }

    adapter = ZitadelAuthAdapter("https://auth.example", "client")
    with pytest.raises(NotAuthorized, match="user missing required OIDC claims"):
        adapter.authenticate("some.jwt.token")
