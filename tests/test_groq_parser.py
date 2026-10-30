import pytest

from backend.services import groq_parser


def test_valid_resume_response_is_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(groq_parser, "_get_client", lambda: object())
    monkeypatch.setattr(
        groq_parser,
        "_call_groq",
        lambda *args: calls.append(args) or '{"name": "Test User", "skills": ["Python"]}',
    )

    result = groq_parser.parse_resume("resume text")

    assert result["skills"] == ["Python"]
    assert len(calls) == 1


def test_invalid_resume_response_retries_once(monkeypatch):
    responses = iter(("not json", '{"name": "Test User"}'))
    calls = []
    monkeypatch.setattr(groq_parser, "_get_client", lambda: object())
    monkeypatch.setattr(
        groq_parser,
        "_call_groq",
        lambda *args: calls.append(args) or next(responses),
    )

    result = groq_parser.parse_resume("resume text")

    assert result["name"] == "Test User"
    assert len(calls) == 2


def test_unparseable_response_error_does_not_include_model_output(monkeypatch):
    monkeypatch.setattr(groq_parser, "_get_client", lambda: object())
    monkeypatch.setattr(
        groq_parser,
        "_call_groq",
        lambda *args: "PRIVATE_RESUME_DATA not json",
    )

    with pytest.raises(ValueError) as error:
        groq_parser.parse_resume("resume text")

    assert "PRIVATE_RESUME_DATA" not in str(error.value)


def test_json_non_object_is_rejected():
    assert groq_parser._try_parse_json('["not", "an object"]') is None
