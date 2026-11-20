import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from backend.services.groq_parser import clean_json_markdown, GroqParser

def test_clean_json_markdown_with_fences():
    raw = "```json\n{\"name\": \"John Doe\", \"skills\": [\"Python\"]}\n```"
    cleaned = clean_json_markdown(raw)
    data = json.loads(cleaned)
    assert data["name"] == "John Doe"
    assert data["skills"] == ["Python"]

def test_clean_json_markdown_with_surrounding_prose():
    raw = "Here is the extracted resume JSON:\n```\n{\"name\": \"Alice\", \"email\": \"alice@test.com\"}\n```\nHope this helps!"
    cleaned = clean_json_markdown(raw)
    data = json.loads(cleaned)
    assert data["name"] == "Alice"
    assert data["email"] == "alice@test.com"

def test_groq_parser_retry_on_malformed_json():
    parser = GroqParser(api_key="test-key")
    mock_client = MagicMock()
    parser.client = mock_client

    # First completion call returns malformed JSON, second call returns valid JSON
    choice1 = MagicMock()
    choice1.message.content = "Not JSON output at all"
    choice2 = MagicMock()
    choice2.message.content = '{"name": "Bob", "skills": ["Go", "Docker"], "experience": [], "education": [], "projects": []}'

    mock_resp1 = MagicMock(choices=[choice1])
    mock_resp2 = MagicMock(choices=[choice2])
    mock_client.chat.completions.create.side_effect = [mock_resp1, mock_resp2]

    res = parser.parse_resume("Resume content here")
    assert res.name == "Bob"
    assert "Go" in res.skills
    assert mock_client.chat.completions.create.call_count == 2

def test_groq_parser_service_error_translation():
    parser = GroqParser(api_key="test-key")
    mock_client = MagicMock()
    parser.client = mock_client

    # Simulate Groq API exception
    mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")

    with pytest.raises(HTTPException) as exc_info:
        parser.parse_resume("Resume text")
    assert exc_info.value.status_code == 502
    assert "groq api error" in exc_info.value.detail.lower()
