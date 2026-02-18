# FieldOps scripts

## Demo seed script (`seed_demo_data.py`)

Seeds the database with realistic demo data: one **owner** (org admin), **N sites** (projects), and **3 supervisors per site**, plus attendance, tasks, daily reports, expense, and materials. Use this to run the app and demo it for sales (e.g. client demos).

### Requirements

- Python 3 with dependencies from backend root: `pip install -r requirements.txt` (or use the same venv as the FastAPI app).
- **Environment variables** (required for actual seed/cleanup):
  - `SUPABASE_URL` – Supabase project URL
  - `SUPABASE_SERVICE_ROLE_KEY` – Service role key (needed to create auth users and write to `fieldops` schema)

Optional env (or CLI):

- `SEED_N_SITES` – Number of sites (default `3`)
- `SEED_DAYS_ATTENDANCE` – Days of attendance to generate (default `14`)
- `SEED_DAYS_REPORTS` – Days of daily reports (default `7`)
- `SEED_PASSWORD` – Password for created users (default `DemoPassword123!`)
- `SEED_DRY_RUN=1` – Only print what would be created; no writes
- `SEED_CLEANUP=1` – Delete seed data (demo tenant and users) instead of seeding

### How to run

From the **backend root** (`fieldops-backend/`):

```bash
# Load env (e.g. from .env)
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Dry run (no DB changes)
python scripts/seed_demo_data.py --dry-run

# Seed data
python scripts/seed_demo_data.py

# Clean up seed data
python scripts/seed_demo_data.py --cleanup
```

CLI options: `--dry-run`, `--cleanup`, `--sites N`, `--days-attendance N`, `--days-reports N`.

### After seeding

- **Tenant ID** and **owner login** (email + password) are printed at the end.
- Owner email: `owner@fieldops-demo.local` (password: `DemoPassword123!` unless you set `SEED_PASSWORD`).
- Supervisors: `supervisor-{site}-{k}@fieldops-demo.local` (same password).
- Log in as the **owner** in your app; the backend resolves `tenant_id` from the JWT `app_metadata` and the owner sees all sites (projects) for that tenant. Use the dashboard to showcase features.

### Notes

- The script creates users in **Supabase Auth** with `app_metadata.tenant_id` set so the FieldOps API can resolve the tenant. No CORE_SERVICE is used.
- Selfie and receipt paths are placeholders (no real files uploaded). The dashboard may show “missing image” for those; that’s acceptable for demos.
- Cleanup removes all data for the demo tenant (projects, tasks, attendance, reports, expense, materials, tenant_members, profiles) and deletes the demo auth users.

### Pitch deck and demo script

See **[DEMO_PITCH_AND_SCRIPT.md](./DEMO_PITCH_AND_SCRIPT.md)** for:
- Slide-by-slide pitch outline (problem, solution, ROI, features, CTA)
- Timed demo script (login → dashboard → sites → wallets → tasks → attendance → materials → daily reports → users)
- Questions to answer to tailor the pitch
- Anticipated technical Q&A (security, API, attendance, wallets, materials, deployment)
