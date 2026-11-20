import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.api.auth import verify_supabase_token, get_current_user
from backend.core.config import settings

SECRET = "test_supabase_jwt_secret_key_12345_32bytes_min"
WRONG_SECRET = "wrong_secret_key_min_32_characters_long_123"

@pytest.fixture(autouse=True)
def set_test_secret(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", SECRET)

def test_verify_token_hs256_success():
    payload = {
        "sub": "user-12345",
        "email": "user@example.com",
        "role": "authenticated",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    decoded = verify_supabase_token(token)
    assert decoded["sub"] == "user-12345"
    assert decoded["email"] == "user@example.com"

def test_verify_token_expired():
    payload = {
        "sub": "user-12345",
        "email": "user@example.com",
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()

def test_verify_token_invalid_signature():
    payload = {
        "sub": "user-12345",
        "email": "user@example.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    token = jwt.encode(payload, WRONG_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_token(token)
    assert exc_info.value.status_code == 401
    assert "signature" in exc_info.value.detail.lower()

def test_verify_token_asymmetric_jwks():
    payload = {
        "sub": "jwks-user-999",
        "email": "jwks@example.com",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    # Mock JWKS client
    mock_key = MagicMock()
    mock_key.key = "fake_public_key"
    
    mock_jwks = MagicMock()
    mock_jwks.get_signing_key_from_jwt.return_value = mock_key

    with patch("backend.api.auth.get_jwks_client", return_value=mock_jwks):
        with patch("jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "key1"}):
            with patch("jwt.decode", return_value=payload):
                res = verify_supabase_token("dummy.rs256.jwt")
                assert res["sub"] == "jwks-user-999"

def test_get_current_user_success():
    payload = {
        "sub": "user-555",
        "email": "tester@test.com",
        "role": "authenticated",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds)
    assert user.id == "user-555"
    assert user.email == "tester@test.com"

def test_get_current_user_missing_credentials():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401
