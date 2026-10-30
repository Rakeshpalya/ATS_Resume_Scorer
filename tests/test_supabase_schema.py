from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261030215000_create_analyses.sql"
)


def test_analyses_migration_matches_application_fields():
    sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    expected_definitions = (
        "id uuid primary key default gen_random_uuid()",
        "user_id uuid not null references auth.users(id) on delete cascade",
        "filename text not null",
        "ats_score double precision not null default 0",
        "keyword_match double precision not null default 0",
        "missing_keywords text[] not null default '{}'::text[]",
        "created_at timestamptz not null default now()",
        "analysis_result jsonb not null",
    )
    for definition in expected_definitions:
        assert definition in sql

    assert "analyses_user_created_at_idx" in sql


def test_analyses_migration_enables_owner_only_rls_without_update_policy():
    sql = MIGRATION_PATH.read_text(encoding="utf-8").lower()

    assert "enable row level security" in sql
    assert "for select" in sql
    assert "for insert" in sql
    assert "for delete" in sql
    assert "using ((select auth.uid()) = user_id)" in sql
    assert "with check ((select auth.uid()) = user_id)" in sql
    assert "for update" not in sql
    assert "using (true)" not in sql
    assert "with check (true)" not in sql
    assert "revoke all on table public.analyses from public, anon" in sql
    assert "grant select, insert, delete on table public.analyses to authenticated" in sql
