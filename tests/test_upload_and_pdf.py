import io
import pytest
from fastapi.testclient import TestClient
import pypdf

from backend.main import app
from backend.services.pdf_export import generate_pdf_report, generate_text_summary
from backend.models.schemas import AnalysisResult, ScoreBreakdown, ParsedResume
from backend.services.resume_parser import extract_hyperlinks_from_pypdf

client = TestClient(app)

def test_upload_unsupported_file_type():
    file_content = b"fake executable content"
    files = {"resume_file": ("malicious.exe", file_content, "application/octet-stream")}
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 422
    assert "unsupported file type" in response.json()["detail"].lower()

def test_upload_file_size_exceeded():
    # 5.5 MB of data
    oversized_content = b"0" * (6 * 1024 * 1024)
    files = {"resume_file": ("large_resume.pdf", oversized_content, "application/pdf")}
    response = client.post("/api/analyze", files=files)
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"].lower()

def test_pdf_hyperlink_extraction():
    # Create an empty in-memory PDF reader to test extract_hyperlinks_from_pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    pdf_bytes_io = io.BytesIO()
    writer.write(pdf_bytes_io)
    pdf_bytes_io.seek(0)

    reader = pypdf.PdfReader(pdf_bytes_io)
    links = extract_hyperlinks_from_pypdf(reader)
    assert isinstance(links, list)

def test_pdf_export_and_text_summary():
    analysis = AnalysisResult(
        id="pdf-test-123",
        filename="sample.pdf",
        created_at="2026-11-20T12:00:00Z",
        scores=ScoreBreakdown(
            formatting_score=19.0,
            keywords_score=24.0,
            content_score=23.0,
            skill_validation_score=15.0,
            ats_compatibility_score=15.0,
            overall_score=96.0,
            interpretation="Excellent"
        ),
        parsed_resume=ParsedResume(
            name="John Doe",
            email="john@example.com",
            skills=["Python", "FastAPI", "Docker"]
        ),
        strengths=["Strong action verbs", "Excellent formatting"],
        action_items=["Keep skills updated"]
    )

    # 1. Text export test
    text_summary = generate_text_summary(analysis)
    assert "John Doe" in text_summary
    assert "96.0 / 100" in text_summary
    assert "Strong action verbs" in text_summary

    # 2. PDF report test
    pdf_bytes, mime = generate_pdf_report(analysis)
    assert len(pdf_bytes) > 0
    assert mime in ["application/pdf", "text/plain"]
