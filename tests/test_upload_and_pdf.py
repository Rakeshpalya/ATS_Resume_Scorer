import asyncio
import io
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from backend.api.auth import AuthenticatedUser
from backend.api import routes
from backend.core.config import MAX_FILE_SIZE_BYTES
from backend.services import pdf_export


def test_upload_limit_is_checked_before_resume_parsing():
    upload = UploadFile(
        file=io.BytesIO(b"x" * (MAX_FILE_SIZE_BYTES + 1)),
        filename="resume.pdf",
    )
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(nlp=None, embedder=None),
        ),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            routes.analyze_resume(
                request,
                upload,
                "",
                AuthenticatedUser("test-user", "test-access-token"),
            )
        )

    assert error.value.status_code == 413
    assert "maximum upload size" in error.value.detail


def test_analysis_passes_verified_identity_and_token_to_history(monkeypatch):
    from backend.services import resume_analyzer, resume_parser
    from backend.database import supabase_db

    upload = UploadFile(file=io.BytesIO(b"fake-pdf"), filename="resume.pdf")
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(nlp=object(), embedder=object()),
        ),
    )
    saved = {}
    monkeypatch.setattr(
        resume_parser,
        "parse_resume_file",
        lambda file_bytes, filename: ("synthetic resume text", {}),
    )
    monkeypatch.setattr(
        resume_analyzer,
        "analyze_full_resume",
        lambda **kwargs: {
            "ats_score": 75,
            "component_scores": {
                "formatting": 75,
                "keywords": 75,
                "content": 75,
                "skill_validation": 75,
                "ats_compatibility": 75,
            },
            "issues_summary": [],
            "detailed_feedback": [],
        },
    )

    async def fake_save_analysis(user_id, filename, analysis_result, access_token):
        saved.update(
            user_id=user_id,
            filename=filename,
            access_token=access_token,
        )
        return "synthetic-analysis-id"

    monkeypatch.setattr(supabase_db, "save_analysis", fake_save_analysis)
    auth = AuthenticatedUser("verified-user-id", "verified-access-token")

    response = asyncio.run(
        routes.analyze_resume(request, upload, "", auth)
    )

    assert response.ats_score == 75
    assert saved == {
        "user_id": "verified-user-id",
        "filename": "resume.pdf",
        "access_token": "verified-access-token",
    }


def test_pdf_export_reports_missing_native_dependencies(monkeypatch):
    monkeypatch.setattr(pdf_export, "WEASYPRINT_INSTALLED", False)

    with pytest.raises(ImportError, match="native libraries"):
        pdf_export.generate_combined_pdf({})
