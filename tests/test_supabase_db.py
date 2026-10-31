import asyncio

import httpx
import pytest
from fastapi import HTTPException

from backend.database import supabase_db
from backend.api import routes
from backend.api.auth import AuthenticatedUser


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


def _history_row(user_id="test-user"):
    return {
        "id": "analysis-1",
        "user_id": user_id,
        "filename": "resume.pdf",
        "ats_score": 80,
        "keyword_match": 72,
        "missing_keywords": ["Python"],
        "created_at": "2026-10-31T00:00:00+00:00",
        "analysis_result": {"ats_score": 80, "component_scores": {}},
    }


def _http_error(status_code, code):
    request = httpx.Request("GET", "https://example.supabase.co/rest/v1/analyses")
    response = httpx.Response(
        status_code,
        json={"code": code, "message": "synthetic database error"},
        request=request,
    )
    return httpx.HTTPStatusError(
        "synthetic failure",
        request=request,
        response=response,
    )


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


def test_history_returns_expected_columns_for_authenticated_user(monkeypatch):
    calls = _configure(monkeypatch, FakeResponse([_history_row()]))

    history = asyncio.run(
        supabase_db.get_user_history("test-user", "test-access-token")
    )

    assert history == [{
        "id": "analysis-1",
        "filename": "resume.pdf",
        "resume_name": "resume.pdf",
        "job_title": "Software Engineer",
        "ats_score": 80,
        "keyword_match": 72,
        "missing_keywords": ["Python"],
        "date": "2026-10-31T00:00:00+00:00",
        "created_at": "2026-10-31T00:00:00+00:00",
        "analysis_result": {"ats_score": 80, "component_scores": {}},
    }]
    method, args, request = calls[0]
    assert method == "GET"
    assert args[0] == "https://example.supabase.co/rest/v1/analyses"
    assert request["params"] == {
        "user_id": "eq.test-user",
        "order": "created_at.desc",
    }
    assert request["headers"]["apikey"] == "test-only-anon-key"
    assert request["headers"]["Authorization"] == "Bearer test-access-token"


def test_history_rejects_rows_outside_authenticated_user_scope(monkeypatch):
    _configure(monkeypatch, FakeResponse([_history_row(user_id="other-user")]))

    with pytest.raises(supabase_db.SupabaseDatabaseError) as error:
        asyncio.run(
            supabase_db.get_user_history("test-user", "test-access-token")
        )

    assert error.value.category == "ownership_violation"
    assert error.value.status_code == 502


def test_history_rejects_incorrect_schema(monkeypatch):
    row = _history_row()
    del row["analysis_result"]
    _configure(monkeypatch, FakeResponse([row]))

    with pytest.raises(supabase_db.SupabaseDatabaseError) as error:
        asyncio.run(
            supabase_db.get_user_history("test-user", "test-access-token")
        )

    assert error.value.category == "schema_mismatch"
    assert error.value.status_code == 503


@pytest.mark.parametrize(
    ("status_code", "code", "category", "expected_status"),
    [
        (401, "PGRST301", "unauthorized", 401),
        (403, "42501", "forbidden", 403),
        (404, "PGRST205", "missing_table", 503),
        (400, "PGRST204", "schema_mismatch", 503),
    ],
)
def test_history_maps_supabase_errors_safely(
    monkeypatch, status_code, code, category, expected_status
):
    _configure(
        monkeypatch,
        FakeResponse(error=_http_error(status_code, code)),
    )

    with pytest.raises(supabase_db.SupabaseDatabaseError) as error:
        asyncio.run(
            supabase_db.get_user_history("test-user", "test-access-token")
        )

    assert error.value.category == category
    assert error.value.status_code == expected_status
    assert "synthetic database error" not in str(error.value)


def test_history_endpoint_returns_safe_supabase_failure(monkeypatch):
    async def fail_history_query(user_id, access_token):
        raise supabase_db.SupabaseDatabaseError(
            "missing_table",
            503,
            "Apply the analyses migration.",
        )

    monkeypatch.setattr(supabase_db, "get_user_history", fail_history_query)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            routes.get_history(
                AuthenticatedUser("test-user", "test-access-token")
            )
        )

    assert error.value.status_code == 503
    assert error.value.detail == "Apply the analyses migration."


def test_history_network_failure_is_reported_as_unavailable(monkeypatch):
    request = httpx.Request("GET", "https://example.supabase.co/rest/v1/analyses")
    _configure(
        monkeypatch,
        FakeResponse(error=httpx.ConnectError("synthetic connection failure", request=request)),
    )

    with pytest.raises(supabase_db.SupabaseDatabaseError) as error:
        asyncio.run(
            supabase_db.get_user_history("test-user", "test-access-token")
        )

    assert error.value.category == "network_error"
    assert error.value.status_code == 503


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
    request = httpx.Request("GET", "https://example.supabase.co/rest/v1/analyses")
    _configure(
        monkeypatch,
        FakeResponse(error=httpx.ConnectError("test-only failure", request=request)),
    )

    with pytest.raises(supabase_db.SupabaseDatabaseError, match="could not be reached"):
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
