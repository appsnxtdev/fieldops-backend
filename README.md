# FieldOps API

FastAPI backend with Supabase (auth, database, storage). No SQLAlchemy; DB access via Supabase client.

## Setup

1. Copy `.env.example` to `.env` and set Supabase credentials.
2. Run SQL in `sql/` against your Supabase project (see sql/README.md).
3. `pip install -r requirements.txt`
4. `uvicorn app.main:app --reload`

## Structure

- `app/core/` – config, dependencies, security
- `app/modules/<feature>/` – schemas, routes, service per feature
- `sql/` – DDL for Supabase
