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

## Production / Cloud Run

- **Env vars**: See `.env.example`. For production use Secret Manager or Cloud Run environment variables; do not commit `.env`. Set `ENV=production`, `DEBUG=false`, and `ALLOWED_ORIGINS` to your frontend origin(s).
- **Build image**: `docker build -t gcr.io/PROJECT_ID/fieldops-backend .` (or use Artifact Registry).
- **Deploy**: `gcloud run deploy fieldops-backend --image gcr.io/PROJECT_ID/fieldops-backend --region REGION --platform managed` and set env vars via `--set-env-vars` or `--set-secrets`. Alternatively use `service.yaml` (replace `PROJECT_ID` and image) with `gcloud run services replace service.yaml`, or run `gcloud builds submit --config=cloudbuild.yaml --substitutions=_REGION=REGION,_SERVICE_NAME=fieldops-backend` to build and deploy in one step.
- **Health**: Liveness/startup use `GET /health`. Optional readiness: `GET /health/ready` (checks Supabase).
