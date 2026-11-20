import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env into os.environ if present
load_dotenv(".env")

logger = logging.getLogger(__name__)

def load_supabase_credentials() -> Dict[str, str]:
    """
    Safely loads Supabase URL, Anon Key, and redirect URL from environment or Streamlit secrets.
    Does not raise exceptions if variables are absent.
    """
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    auth_redirect_url = os.getenv("AUTH_REDIRECT_URL", "http://localhost:8501")

    # Fallback to streamlit secrets if running inside streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if not supabase_url and "SUPABASE_URL" in st.secrets:
                supabase_url = str(st.secrets["SUPABASE_URL"])
            if not supabase_anon_key and "SUPABASE_ANON_KEY" in st.secrets:
                supabase_anon_key = str(st.secrets["SUPABASE_ANON_KEY"])
            if "AUTH_REDIRECT_URL" in st.secrets:
                auth_redirect_url = str(st.secrets["AUTH_REDIRECT_URL"])
    except Exception:
        pass

    return {
        "url": supabase_url.strip(),
        "anon_key": supabase_anon_key.strip(),
        "redirect_url": auth_redirect_url.strip()
    }

def humanize_auth_error(error: Exception) -> str:
    """Translates raw Supabase and network auth error messages into user-friendly text."""
    msg = str(error).lower()
    if "invalid login credentials" in msg or "invalid_grant" in msg:
        return "Incorrect email or password. Please check your credentials and try again."
    if "user already registered" in msg or "already exists" in msg:
        return "An account with this email address already exists. Please sign in instead."
    if "email not confirmed" in msg:
        return "Please verify your email address via the confirmation link sent to your inbox."
    if "password should be at least" in msg:
        return "Password is too weak. Please use at least 6 characters."
    if "rate limit" in msg:
        return "Too many attempts. Please wait a moment and try again."
    if "network" in msg or "connection" in msg:
        return "Network connection issue. Please check your internet connection."
    return f"Authentication error: {str(error)}"

class SupabaseAuthService:
    def __init__(self):
        self._client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        creds = load_supabase_credentials()
        self.url = creds["url"]
        self.anon_key = creds["anon_key"]
        self.redirect_url = creds["redirect_url"]
        if self.url and self.anon_key:
            try:
                self._client = create_client(self.url, self.anon_key)
            except Exception as e:
                logger.warning(f"Could not initialize Supabase client: {e}")
                self._client = None
        else:
            self._client = None

    def get_client(self) -> Optional[Client]:
        if self._client is None:
            self._init_client()
        return self._client

    def is_configured(self) -> bool:
        creds = load_supabase_credentials()
        return bool(creds["url"] and creds["anon_key"])

    def sign_in_with_password(self, email: str, password: str) -> Dict[str, Any]:
        client = self.get_client()
        if not client:
            raise RuntimeError("Supabase credentials are not configured.")
        try:
            res = client.auth.sign_in_with_password({"email": email, "password": password})
            return {
                "user": res.user,
                "session": res.session,
                "access_token": res.session.access_token if res.session else None
            }
        except Exception as e:
            raise ValueError(humanize_auth_error(e))

    def sign_up_with_password(self, email: str, password: str) -> Dict[str, Any]:
        client = self.get_client()
        if not client:
            raise RuntimeError("Supabase credentials are not configured.")
        try:
            res = client.auth.sign_up({"email": email, "password": password})
            return {
                "user": res.user,
                "session": res.session,
                "access_token": res.session.access_token if res.session else None
            }
        except Exception as e:
            raise ValueError(humanize_auth_error(e))

    def get_oauth_google_url(self) -> str:
        creds = load_supabase_credentials()
        url = creds["url"]
        redirect_url = creds["redirect_url"] or "http://localhost:8501"

        client = self.get_client()
        if client:
            try:
                res = client.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {
                        "redirect_to": redirect_url
                    }
                })
                if res and getattr(res, "url", None):
                    return res.url
            except Exception as e:
                logger.warning(f"client.auth.sign_in_with_oauth error: {e}")

        # Fallback to direct Supabase OAuth authorize endpoint
        if url:
            base = url.rstrip("/")
            return f"{base}/auth/v1/authorize?provider=google&redirect_to={redirect_url}"

        raise RuntimeError("Supabase URL is not configured.")

    def exchange_code_for_session(self, auth_code: str) -> Optional[Dict[str, Any]]:
        client = self.get_client()
        if not client:
            return None
        try:
            res = client.auth.exchange_code_for_session({"auth_code": auth_code})
            return {
                "user": res.user,
                "session": res.session,
                "access_token": res.session.access_token if res.session else None
            }
        except Exception as e:
            logger.warning(f"Failed to exchange code: {e}")
            return None

    def sign_out(self):
        client = self.get_client()
        if client:
            try:
                client.auth.sign_out()
            except Exception:
                pass

supabase_auth = SupabaseAuthService()
