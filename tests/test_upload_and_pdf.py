import asyncio
import io
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from backend.api.auth import AuthenticatedUser
from backend.api import routes
from backend.core.config import MAX_FILE_SIZE_BYTES
from backend.services import groq_parser, resume_parser
from backend.services import pdf_export


def _text_pdf(text="Resume text"):
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream + b"\nendstream",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(document)


def test_extract_text_from_valid_text_pdf():
    assert "Resume text" in resume_parser.extract_text_from_pdf(_text_pdf())


def test_empty_pdf_returns_extraction_error():
    with pytest.raises(resume_parser.FileParsingError, match="Failed to extract text"):
        resume_parser.extract_text_from_pdf(_text_pdf(""))


def test_malformed_pdf_returns_extraction_error():
    with pytest.raises(resume_parser.FileParsingError, match="Failed to extract text"):
        resume_parser.extract_text_from_pdf(b"%PDF-1.4\nbroken")


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


def test_analysis_returns_actionable_provider_error(monkeypatch):
    from backend.services import resume_analyzer

    upload = UploadFile(file=io.BytesIO(b"fake-pdf"), filename="resume.pdf")
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(nlp=object(), embedder=object())),
    )
    monkeypatch.setattr(
        resume_parser,
        "parse_resume_file",
        lambda file_bytes, filename: ("synthetic resume text", {}),
    )
    monkeypatch.setattr(
        resume_analyzer,
        "analyze_full_resume",
        lambda **kwargs: (_ for _ in ()).throw(
            groq_parser.GroqServiceError(
                "model_unavailable", 503, "Configured AI model is unavailable."
            )
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

    assert error.value.status_code == 503
    assert error.value.detail == "Configured AI model is unavailable."


def test_empty_resume_is_rejected_before_analysis(monkeypatch):
    upload = UploadFile(file=io.BytesIO(b"fake-pdf"), filename="resume.pdf")
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(nlp=object(), embedder=object())),
    )

    def reject_empty_resume(file_bytes, filename):
        raise resume_parser.FileParsingError("No text could be extracted from the PDF.")

    monkeypatch.setattr(resume_parser, "parse_resume_file", reject_empty_resume)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            routes.analyze_resume(
                request,
                upload,
                "",
                AuthenticatedUser("test-user", "test-access-token"),
            )
        )

    assert error.value.status_code == 422
    assert "No text could be extracted" in error.value.detail


def test_pdf_export_reports_missing_native_dependencies(monkeypatch):
    monkeypatch.setattr(pdf_export, "WEASYPRINT_INSTALLED", False)

    with pytest.raises(ImportError, match="native libraries"):
        pdf_export.generate_combined_pdf({})
