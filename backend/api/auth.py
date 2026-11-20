import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient, ExpiredSignatureError, InvalidTokenError

from backend.core.config import settings
from backend.models.schemas import UserProfile

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Cached JWK client if Supabase URL is present
_jwks_client: Optional[PyJWKClient] = None

def get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None and settings.SUPABASE_URL:
        # Supabase JWKS endpoint: {SUPABASE_URL}/auth/v1/.well-known/jwks.json
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            _jwks_client = PyJWKClient(jwks_url)
        except Exception as e:
            logger.warning(f"Could not initialize PyJWKClient for {jwks_url}: {e}")
    return _jwks_client

def verify_supabase_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Supabase JWT token:
    1. Checks header 'alg'. If asymmetric (ES256, RS256), verifies using JWKS.
    2. Falls back to HS256 with SUPABASE_JWT_SECRET if secret is provided or alg is HS256.
    """
    try:
        unverified_headers = jwt.get_unverified_header(token)
        alg = unverified_headers.get("alg", "HS256")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token format or header: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Asymmetric verification (ES256, RS256) via JWKS
    if alg in ["ES256", "RS256"]:
        jwks_client = get_jwks_client()
        if jwks_client:
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=[alg],
                    options={"verify_aud": False}
                )
                return payload
            except ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except Exception as e:
                logger.warning(f"JWKS verification failed for alg {alg}: {e}")

    # 2. Symmetric verification (HS256) or fallback to SUPABASE_JWT_SECRET
    secret = settings.SUPABASE_JWT_SECRET
    if not secret:
        # If no secret configured and JWKS didn't succeed, but token is valid jwt format,
        # in test / local development without secret configured:
        try:
            payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
            return payload
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token signature and no JWT secret configured: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256", "HS384", "HS512"],
            options={"verify_aud": False}
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token signature: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserProfile:
    """Dependency that requires an authenticated user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_supabase_token(token)

    sub = payload.get("sub") or payload.get("user_id")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject (sub).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserProfile(
        id=str(sub),
        email=payload.get("email"),
        role=payload.get("role", "authenticated")
    )

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserProfile]:
    """Dependency that optionally extracts user if valid token is provided."""
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = verify_supabase_token(credentials.credentials)
        sub = payload.get("sub") or payload.get("user_id")
        if sub:
            return UserProfile(
                id=str(sub),
                email=payload.get("email"),
                role=payload.get("role", "authenticated")
            )
    except Exception:
        return None
    return None
