import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from backend.database.supabase_db import SupabaseDBClient
from backend.models.schemas import (
    AnalysisResult,
    ScoreBreakdown,
    ParsedResume
)

@pytest.fixture
def sample_analysis():
    return AnalysisResult(
        id="test-analysis-123",
        filename="resume.pdf",
        created_at="2026-11-20T12:00:00Z",
        scores=ScoreBreakdown(
            formatting_score=18.0,
            keywords_score=22.0,
            content_score=20.0,
            skill_validation_score=14.0,
            ats_compatibility_score=15.0,
            overall_score=89.0,
            interpretation="Excellent"
        ),
        parsed_resume=ParsedResume(
            name="Alice",
            skills=["Python", "FastAPI"]
        )
    )

@pytest.mark.asyncio
async def test_supabase_db_fallback_in_memory(sample_analysis):
    client = SupabaseDBClient()
    client.supabase_url = ""
    client.anon_key = ""

    saved = await client.save_analysis("user-abc", None, sample_analysis)
    assert saved["id"] == "test-analysis-123"
    assert saved["user_id"] == "user-abc"

    history = await client.get_user_analyses("user-abc", None)
    assert len(history) == 1
    assert history[0].id == "test-analysis-123"
    assert history[0].ats_score == 89.0

    deleted = await client.delete_analysis("test-analysis-123", "user-abc", None)
    assert deleted is True

    history_after = await client.get_user_analyses("user-abc", None)
    assert len(history_after) == 0

@pytest.mark.asyncio
async def test_supabase_db_remote_headers_and_error(sample_analysis):
    client = SupabaseDBClient()
    client.supabase_url = "https://mock.supabase.co"
    client.anon_key = "mock_anon_key"

    headers = client._get_headers("custom_user_jwt")
    assert headers["apikey"] == "mock_anon_key"
    assert headers["Authorization"] == "Bearer custom_user_jwt"

    # Test error code PGRST204 / PGRST205 handling
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "PGRST204: Could not find the table 'analyses' in the schema cache"

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(HTTPException) as exc_info:
            await client.save_analysis("user-abc", "custom_user_jwt", sample_analysis)
        assert exc_info.value.status_code == 500
        assert "schema mismatch" in exc_info.value.detail.lower()
