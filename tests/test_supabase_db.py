import asyncio

import pytest

from backend.database import supabase_db


class FakeResponse:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.data


class FakeAsyncClient:
    def __init__(self, response, calls):
        self.response = response
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def post(self, *args, **kwargs):
        self.calls.append(("POST", args, kwargs))
        return self.response

    async def get(self, *args, **kwargs):
        self.calls.append(("GET", args, kwargs))
        return self.response

    async def delete(self, *args, **kwargs):
        self.calls.append(("DELETE", args, kwargs))
        return self.response


def _configure(monkeypatch, response):
    calls = []
    monkeypatch.setattr(supabase_db, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(supabase_db, "SUPABASE_ANON_KEY", "test-only-anon-key")
    monkeypatch.setattr(
        supabase_db.httpx,
        "AsyncClient",
        lambda: FakeAsyncClient(response, calls),
    )
    return calls


def test_save_analysis_returns_inserted_id(monkeypatch):
    calls = _configure(monkeypatch, FakeResponse([{"id": "analysis-1"}]))

    analysis_id = asyncio.run(
        supabase_db.save_analysis(
            "test-user",
            "resume.pdf",
            {"ats_score": 80},
            "test-access-token",
        )
    )

    assert analysis_id == "analysis-1"
    method, _, request = calls[0]
    assert method == "POST"
    assert request["headers"]["apikey"] == "test-only-anon-key"
    assert request["headers"]["Authorization"] == "Bearer test-access-token"
    assert request["json"]["user_id"] == "test-user"


def test_unconfigured_history_raises_instead_of_looking_empty(monkeypatch):
    monkeypatch.setattr(supabase_db, "SUPABASE_URL", "")
    monkeypatch.setattr(supabase_db, "SUPABASE_ANON_KEY", "")

    with pytest.raises(RuntimeError, match="not configured"):
        asyncio.run(supabase_db.get_user_history("test-user", "test-access-token"))


def test_delete_reports_not_found_when_no_row_was_deleted(monkeypatch):
    calls = _configure(monkeypatch, FakeResponse([]))

    deleted = asyncio.run(
        supabase_db.delete_analysis("missing", "test-user", "test-access-token")
    )

    assert deleted is False
    method, _, request = calls[0]
    assert method == "DELETE"
    assert request["params"] == {"id": "eq.missing", "user_id": "eq.test-user"}
    assert request["headers"]["Authorization"] == "Bearer test-access-token"


def test_supabase_request_failure_is_not_returned_as_empty_history(monkeypatch):
    _configure(monkeypatch, FakeResponse(error=ValueError("test-only failure")))

    with pytest.raises(RuntimeError, match="Could not fetch history"):
        asyncio.run(supabase_db.get_user_history("test-user", "test-access-token"))


def test_history_query_is_scoped_to_authenticated_user(monkeypatch):
    calls = _configure(monkeypatch, FakeResponse([]))

    history = asyncio.run(
        supabase_db.get_user_history("test-user", "test-access-token")
    )

    assert history == []
    method, _, request = calls[0]
    assert method == "GET"
    assert request["params"] == {
        "user_id": "eq.test-user",
        "order": "created_at.desc",
    }
    assert request["headers"]["Authorization"] == "Bearer test-access-token"
