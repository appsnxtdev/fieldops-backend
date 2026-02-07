-- Run AFTER 001-009. Exposes fieldops schema to PostgREST so the API can query it.
-- Fixes: PGRST106 "The schema must be one of the following: public, graphql_public"

GRANT USAGE ON SCHEMA fieldops TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA fieldops TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA fieldops TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA fieldops TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA fieldops GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA fieldops GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;

-- On Supabase Cloud: also add "fieldops" in Dashboard → Project Settings → API → Exposed schemas.
-- Then run: NOTIFY pgrst, 'reload schema';
NOTIFY pgrst, 'reload schema';
