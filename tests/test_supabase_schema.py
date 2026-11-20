import os
import pytest

MIGRATION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "supabase",
    "migrations",
    "20261030215000_create_analyses.sql"
)

def test_migration_file_exists():
    assert os.path.exists(MIGRATION_PATH), f"Migration file not found at {MIGRATION_PATH}"

def test_migration_schema_ddl():
    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        sql = f.read()

    assert "CREATE TABLE public.analyses" in sql
    assert "user_id uuid NOT NULL REFERENCES auth.users(id)" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "analyses_select_own" in sql
    assert "analyses_insert_own" in sql
    assert "analyses_delete_own" in sql
    assert "auth.uid()" in sql
