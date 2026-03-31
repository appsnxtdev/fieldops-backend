# FieldOps scripts

## Demo seed script (`seed_demo_data.py`)

Seeds the database with realistic demo data: one **owner** (org admin), **N sites** (projects), and **3 supervisors per site**, plus attendance, tasks, daily reports, expense, materials, and labour. Use this to run the app and demo it for sales (e.g. client demos).

### Requirements

- Python 3 with dependencies from backend root: `pip install -r requirements.txt` (or use the same venv as the FastAPI app).
- **Environment variables** (required for actual seed/cleanup):
  - `SUPABASE_URL` – Supabase project URL
  - `SUPABASE_SERVICE_ROLE_KEY` – Service role key (needed to create auth users and write to `fieldops` schema)

Optional env (or CLI):

- `SEED_TENANT_ID` – Use specific tenant ID (default: generates new UUID)
- `SEED_N_SITES` – Number of sites (default `3`)
- `SEED_DAYS_ATTENDANCE` – Days of attendance to generate (default `14`)
- `SEED_DAYS_REPORTS` – Days of daily reports (default `7`)
- `SEED_DAYS_LABOUR` – Days of labour counts (default `14`)
- `SEED_DRY_RUN=1` – Only print what would be created; no writes
- `SEED_CLEANUP=1` – Delete seed data (demo tenant and users) instead of seeding

### How to run

From the **backend root** (`fieldops-backend/`):

#### Step 1: Print required accounts

```bash
# Set environment variables
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Print required user accounts to create
python scripts/seed_demo_data.py --print-accounts
```

This will output the tenant name, owner, and supervisor names/emails that need to be created manually in your user management system.

#### Step 2: Create users manually

Create the users shown in Step 1 using your core service or Supabase Auth. Note down the user IDs.

#### Step 3: Run the seed script

```bash
# Set required user IDs
export SEED_OWNER_ID=<owner_uuid>
export SEED_SUPERVISOR_IDS=<id1>,<id2>,<id3>,<id4>,<id5>,<id6>,<id7>,<id8>,<id9>

# Optional: set tenant ID (otherwise generates new one)
export SEED_TENANT_ID=<tenant_uuid>

# Dry run (check what would be created, no DB changes)
python scripts/seed_demo_data.py --dry-run

# Seed data
python scripts/seed_demo_data.py

# Clean up seed data
python scripts/seed_demo_data.py --cleanup
```

CLI options: `--dry-run`, `--cleanup`, `--print-accounts`, `--sites N`, `--days-attendance N`, `--days-reports N`, `--days-labour N`.

**Example with custom parameters:**

```bash
# Seed with 5 sites, 30 days of attendance, 14 days of reports and labour
python scripts/seed_demo_data.py --sites 5 --days-attendance 30 --days-reports 14 --days-labour 14
```

### What gets seeded

The script creates comprehensive demo data including:

- **Profiles and tenant members**: Owner (org_admin) + 3 supervisors per site (members)
- **Projects**: N sites with realistic names, addresses, and coordinates (Bangalore area)
- **Project members**: 3 supervisors per site (1 admin, 2 members)
- **Tasks**: 6-12 tasks per project with statuses (To Do, In Progress, Done) and task updates
- **Attendance**: Last N days of check-in/out records for all supervisors
- **Daily reports**: Last N days of reports with note entries
- **Expense transactions**: Credit and debit entries per project
- **Labour**:
  - 7 labour types at tenant level (Mason, Helper, Carpenter, etc.) with daily rates
  - Daily labour counts per project for last N days
- **Materials**:
  - 8 master materials in tenant catalog (Cement, Sand, Steel, etc.)
  - Project-specific materials with ledger entries (in/out transactions)

### After seeding

- **Tenant ID** is printed at the end
- Log in using the user credentials you created in Step 2
- The backend resolves `tenant_id` from tenant_members table
- The owner (org_admin) sees all sites (projects) for that tenant
- Supervisors only see their assigned projects

### Notes

- The script **does NOT create Auth users**. You must create them manually first (see Step 1-2 above).
- User emails follow pattern: `firstname.lastname@fieldops.demo`
- Selfie and receipt paths are placeholders (no real files uploaded). The dashboard may show “missing image” for those; that’s acceptable for demos.
- Cleanup removes all data for the demo tenant:
  - Projects and project members
  - Tasks and task updates
  - Attendance records
  - Daily reports and entries
  - Expense transactions
  - Labour types and daily labour counts
  - Materials and material ledger
  - Tenant members and profiles
- Labour types include common construction roles with realistic daily rates in INR (₹500-900/day)

### Pitch deck and demo script

See **[DEMO_PITCH_AND_SCRIPT.md](./DEMO_PITCH_AND_SCRIPT.md)** for:
- Slide-by-slide pitch outline (problem, solution, ROI, features, CTA)
- Timed demo script (login → dashboard → sites → wallets → tasks → attendance → materials → daily reports → users)
- Questions to answer to tailor the pitch
- Anticipated technical Q&A (security, API, attendance, wallets, materials, deployment)
