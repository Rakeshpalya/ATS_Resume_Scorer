from frontend.services.supabase_client import _humanize


def test_unknown_auth_error_does_not_expose_exception_details():
    error = _humanize(Exception("response contained access_token=private-value"))

    assert error == "Authentication request failed. Please try again."
    assert "private-value" not in error


def test_known_auth_errors_remain_actionable():
    assert _humanize(Exception("Invalid login credentials")) == "Wrong email or password"
