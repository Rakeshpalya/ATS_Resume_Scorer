import time

import jwt
import pytest

from backend.api import auth
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


TEST_SECRET = "test-only-signing-secret-long-enough-for-hs256"
SUPABASE_URL = "https://example.supabase.co"


def _token(
    *,
    issuer=f"{SUPABASE_URL}/auth/v1",
    audience="authenticated",
    secret=TEST_SECRET,
    expiration=None,
):
    if expiration is None:
        expiration = int(time.time()) + 300
    return jwt.encode(
        {
            "sub": "test-user",
            "aud": audience,
            "iss": issuer,
            "exp": expiration,
        },
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def configured_hs256_auth(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", TEST_SECRET)


def test_hs256_valid_token_is_accepted(configured_hs256_auth):
    payload = auth._verify_token(_token())

    assert payload["sub"] == "test-user"


def test_hs256_token_with_wrong_issuer_is_rejected(configured_hs256_auth):
    with pytest.raises(jwt.InvalidIssuerError):
        auth._verify_token(_token(issuer="https://attacker.example/auth/v1"))


def test_hs256_token_with_wrong_audience_is_rejected(configured_hs256_auth):
    with pytest.raises(jwt.InvalidAudienceError):
        auth._verify_token(_token(audience="other"))


def test_hs256_token_with_invalid_signature_is_rejected(configured_hs256_auth):
    with pytest.raises(jwt.InvalidSignatureError):
        auth._verify_token(
            _token(secret="different-test-signing-secret-long-enough-for-hs256")
        )


def test_hs256_expired_token_is_rejected(configured_hs256_auth):
    with pytest.raises(jwt.ExpiredSignatureError):
        auth._verify_token(_token(expiration=int(time.time()) - 1))


def test_expired_history_access_token_returns_401(configured_hs256_auth):
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=_token(expiration=int(time.time()) - 1),
    )

    with pytest.raises(HTTPException) as error:
        auth.get_authenticated_user(credentials)

    assert error.value.status_code == 401


def test_authenticated_user_context_preserves_verified_access_token(configured_hs256_auth):
    token = _token()
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    user = auth.get_authenticated_user(credentials)

    assert user.user_id == "test-user"
    assert user.access_token == token


def test_missing_supabase_url_is_reported_as_server_configuration_error(monkeypatch):
    monkeypatch.setattr(auth, "SUPABASE_URL", "")
    monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", TEST_SECRET)

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="not-a-real-token",
    )
    with pytest.raises(HTTPException) as error:
        auth.get_current_user(credentials)

    assert error.value.status_code == 500
