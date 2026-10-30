from pathlib import Path

from frontend.services import supabase_client


def test_root_env_loading_whitelists_only_public_frontend_values():
    assert set(supabase_client._LOCAL_PUBLIC_CONFIG) <= {
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "AUTH_REDIRECT_URL",
    }
    assert "SUPABASE_KEY" not in supabase_client._LOCAL_PUBLIC_CONFIG


def test_root_env_parser_never_parses_service_role_entry(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SUPABASE_URL=https://example.supabase.co\n"
        "SUPABASE_KEY=private-test-only-value\n"
        "SUPABASE_ANON_KEY=public-test-only-value\n"
        "GROQ_API_KEY=private-test-only-value\n",
        encoding="utf-8",
    )

    parsed = supabase_client._load_public_dotenv(Path(env_file))

    assert parsed["SUPABASE_URL"] == "https://example.supabase.co"
    assert parsed["SUPABASE_ANON_KEY"] == "public-test-only-value"
    assert "SUPABASE_KEY" not in parsed
    assert "GROQ_API_KEY" not in parsed
