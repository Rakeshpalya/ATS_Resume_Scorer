import io
import os
import logging
import re
from pathlib import Path
from typing import Any, Dict
import streamlit as st
from supabase import Client, create_client

logger = logging.getLogger('ats_resume_scorer')

_PUBLIC_ENV_KEYS = ('SUPABASE_URL', 'SUPABASE_ANON_KEY', 'AUTH_REDIRECT_URL')


def _load_public_dotenv(path: Path) -> Dict[str, str]:
    try:
        from dotenv import dotenv_values
    except ImportError:
        return {}

    allowed = set(_PUBLIC_ENV_KEYS)
    public_lines = []
    try:
        with path.open(encoding='utf-8') as env_file:
            for line in env_file:
                match = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
                if match and match.group(1) in allowed:
                    public_lines.append(line)
    except FileNotFoundError:
        return {}

    parsed = dotenv_values(stream=io.StringIO(''.join(public_lines)))
    return {key: parsed.get(key, '') or '' for key in _PUBLIC_ENV_KEYS}


_LOCAL_PUBLIC_CONFIG = _load_public_dotenv(
    Path(__file__).resolve().parents[2] / '.env'
)


def _secret(key: str, section: str = 'supabase') -> str:
    """Read public frontend config without parsing private root .env entries."""
    val = os.getenv(key, '')
    if not val:
        val = _LOCAL_PUBLIC_CONFIG.get(key, '')
    if val:
        return val
    try:
        return st.secrets[section][key]
    except (KeyError, FileNotFoundError, AttributeError):
        return ''


SUPABASE_URL = _secret('SUPABASE_URL')
SUPABASE_ANON_KEY = _secret('SUPABASE_ANON_KEY')

OAUTH_REDIRECT_URL = (
    _secret('AUTH_REDIRECT_URL')
    or _secret('redirect_uri', 'google_oauth')
    or 'http://localhost:8501'
)


def _missing_config() -> str | None:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return 'Supabase is not configured — set SUPABASE_URL and SUPABASE_ANON_KEY in .env or .streamlit/secrets.toml'
    return None


@st.cache_resource
def get_client() -> Client | None:
    """Cached singleton — preserves PKCE state across Streamlit reruns."""
    if _missing_config():
        return None
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def _session_dict(session, user) -> Dict[str, Any]:
    return {
        'access_token':  session.access_token,
        'refresh_token': session.refresh_token,
        'user_id':       user.id,
        'email':         user.email,
    }


def sign_in_with_password(email: str, password: str) -> Dict[str, Any]:
    err = _missing_config()
    if err:
        return {'error': err}
    try:
        resp = get_client().auth.sign_in_with_password(
            {'email': email, 'password': password}
        )
        if not resp.session or not resp.user:
            return {'error': 'Invalid credentials'}
        return _session_dict(resp.session, resp.user)
    except Exception as exc:
        logger.warning("sign_in_with_password failed (%s)", type(exc).__name__)
        return {'error': _humanize(exc)}


def sign_up_with_password(email: str, password: str) -> Dict[str, Any]:
    err = _missing_config()
    if err:
        return {'error': err}
    try:
        resp = get_client().auth.sign_up({'email': email, 'password': password})
        if resp.session and resp.user:
            return _session_dict(resp.session, resp.user)
        if resp.user:
            return {'pending_confirmation': True, 'email': email}
        return {'error': 'Sign-up failed'}
    except Exception as exc:
        logger.warning("sign_up failed (%s)", type(exc).__name__)
        return {'error': _humanize(exc)}


def google_oauth_url() -> Dict[str, Any]:
    err = _missing_config()
    if err:
        return {'error': err}
    try:
        resp = get_client().auth.sign_in_with_oauth({
            'provider': 'google',
            'options': {'redirect_to': OAUTH_REDIRECT_URL},
        })
        return {'url': resp.url}
    except Exception as exc:
        logger.warning("oauth url generation failed (%s)", type(exc).__name__)
        return {'error': _humanize(exc)}


def exchange_code_for_session(auth_code: str) -> Dict[str, Any]:
    """Called once after the OAuth provider redirects back with `?code=...`."""
    err = _missing_config()
    if err:
        return {'error': err}
    client = get_client()
    try:
        storage_key = f'{client.auth._storage_key}-code-verifier'
        code_verifier = client.auth._storage.get_item(storage_key) or ''
        resp = client.auth.exchange_code_for_session({
            'auth_code': auth_code,
            'code_verifier': code_verifier,
            'redirect_to': OAUTH_REDIRECT_URL,
        })
        if not resp.session or not resp.user:
            return {'error': 'OAuth exchange returned no session'}
        return _session_dict(resp.session, resp.user)
    except Exception as exc:
        logger.warning("exchange_code_for_session failed (%s)", type(exc).__name__)
        return {'error': _humanize(exc)}


def sign_out() -> None:
    if _missing_config():
        return
    try:
        get_client().auth.sign_out()
    except Exception as exc:
        logger.warning("sign_out failed (%s)", type(exc).__name__)


def _humanize(exc: Exception) -> str:
    msg = str(exc)
    # supabase errors arrive as "<status>: {json blob}" — surface the human bit
    if 'invalid_grant' in msg.lower() or 'invalid login' in msg.lower():
        return 'Wrong email or password'
    if 'user already registered' in msg.lower() or 'already been registered' in msg.lower():
        return 'An account with this email already exists — try signing in'
    if 'password should be at least' in msg.lower():
        return 'Password too short (Supabase default is 6 characters)'
    return 'Authentication request failed. Please try again.'
