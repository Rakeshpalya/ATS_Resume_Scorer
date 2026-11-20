import pytest
from frontend.services.supabase_client import humanize_auth_error

def test_humanize_invalid_credentials():
    err = Exception("Invalid login credentials")
    msg = humanize_auth_error(err)
    assert "Incorrect email or password" in msg

def test_humanize_user_already_registered():
    err = Exception("User already registered")
    msg = humanize_auth_error(err)
    assert "already exists" in msg

def test_humanize_email_not_confirmed():
    err = Exception("Email not confirmed")
    msg = humanize_auth_error(err)
    assert "verify your email address" in msg

def test_humanize_weak_password():
    err = Exception("Password should be at least 6 characters")
    msg = humanize_auth_error(err)
    assert "Password is too weak" in msg

def test_humanize_generic_error():
    err = Exception("Unexpected server timeout")
    msg = humanize_auth_error(err)
    assert "Authentication error" in msg
    assert "Unexpected server timeout" in msg
