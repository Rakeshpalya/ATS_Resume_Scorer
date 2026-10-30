-- Verify that public.analyses does not already exist before applying.
-- This migration intentionally fails on an existing table so its schema is not hidden.
CREATE TABLE public.analyses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename text NOT NULL,
    ats_score double precision NOT NULL DEFAULT 0,
    keyword_match double precision NOT NULL DEFAULT 0,
    missing_keywords text[] NOT NULL DEFAULT '{}'::text[],
    created_at timestamptz NOT NULL DEFAULT now(),
    analysis_result jsonb NOT NULL
        CHECK (jsonb_typeof(analysis_result) = 'object')
);

CREATE INDEX analyses_user_created_at_idx
    ON public.analyses (user_id, created_at DESC);

ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.analyses FROM PUBLIC, anon;
GRANT SELECT, INSERT, DELETE ON TABLE public.analyses TO authenticated;

CREATE POLICY analyses_select_own
    ON public.analyses
    FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY analyses_insert_own
    ON public.analyses
    FOR INSERT
    TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY analyses_delete_own
    ON public.analyses
    FOR DELETE
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);
