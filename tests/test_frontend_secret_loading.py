import os
from unittest.mock import patch
from frontend.services.supabase_client import load_supabase_credentials

def test_load_credentials_from_environment(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://xyz.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key-12345")
    monkeypatch.setenv("AUTH_REDIRECT_URL", "http://localhost:8501")

    creds = load_supabase_credentials()
    assert creds["url"] == "https://xyz.supabase.co"
    assert creds["anon_key"] == "anon-key-12345"
    assert creds["redirect_url"] == "http://localhost:8501"

def test_load_credentials_empty_env_safe(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("AUTH_REDIRECT_URL", raising=False)

    creds = load_supabase_credentials()
    assert isinstance(creds, dict)
    assert creds["url"] == ""
    assert creds["anon_key"] == ""
    assert creds["redirect_url"] == "http://localhost:8501"
