from types import SimpleNamespace
from unittest.mock import Mock

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

    with pytest.raises(groq_parser.GroqServiceError) as error:
        groq_parser.parse_resume("resume text")

    assert "PRIVATE_RESUME_DATA" not in str(error.value)


def test_json_non_object_is_rejected():
    assert groq_parser._try_parse_json('["not", "an object"]') is None


def test_groq_model_uses_documented_replacement():
    assert groq_parser.GROQ_MODEL == "openai/gpt-oss-120b"


@pytest.mark.parametrize(
    ("error_type", "expected_status", "expected_category"),
    [
        ("APITimeoutError", 504, "timeout"),
        ("RateLimitError", 503, "rate_limit"),
        ("AuthenticationError", 503, "configuration"),
        ("NotFoundError", 503, "model_unavailable"),
        ("APIConnectionError", 503, "connection"),
        ("APIStatusError", 502, "provider_error"),
    ],
)
def test_groq_sdk_errors_are_classified_without_provider_details(
    monkeypatch, error_type, expected_status, expected_category
):
    error = type(
        "SdkError",
        (Exception,),
        {"status_code": 429},
    )("private provider message")
    monkeypatch.setattr(
        groq_parser,
        error_type,
        type(error),
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=Mock(side_effect=error))
        )
    )

    with pytest.raises(groq_parser.GroqServiceError) as caught:
        groq_parser._call_groq(client, "system", "prompt")

    assert caught.value.status_code == expected_status
    assert caught.value.category == expected_category
    assert "private provider message" not in str(caught.value)


def test_empty_groq_response_becomes_safe_service_error():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=" "))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=Mock(return_value=response))
        )
    )

    with pytest.raises(groq_parser.GroqServiceError) as error:
        groq_parser._call_groq(client, "system", "prompt")

    assert error.value.category == "invalid_response"
    assert error.value.status_code == 502
