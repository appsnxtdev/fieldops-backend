# SQL migrations

DDL for Supabase. All application tables live in the **fieldops** schema (not public). Run in order (001, 002, …) via Supabase Dashboard → SQL Editor.

- **001_init_extensions.sql** – extensions + `CREATE SCHEMA fieldops`
- **002_users.sql** – fieldops.profiles
- **003_tenant_members.sql** – fieldops.tenant_members
- **004_projects.sql** – fieldops.projects, fieldops.project_members
- **005_attendance.sql** – fieldops.attendance
- **006_tasks.sql** – fieldops.project_task_statuses, fieldops.tasks
- **007_daily_reports.sql** – fieldops.daily_reports, fieldops.daily_report_entries
- **008_materials.sql** – fieldops.materials, fieldops.material_ledger
- **009_expense.sql** – fieldops.expense_transactions
- **010_expose_fieldops_schema.sql** – grants and expose `fieldops` to PostgREST (fixes PGRST106). Run this last.
- **011_projects_extra_fields.sql** – add location, address, project_admin_user_id to projects.

**If you see PGRST106** (schema must be public or graphql_public): run **010_expose_fieldops_schema.sql** in the SQL Editor.

**Supabase**: Expose the `fieldops` schema in the API (Dashboard → Settings → API → “Exposed schemas” or PostgREST config) so the client can query it. Create storage buckets `attendance`, `daily_reports`, `expense` if using file uploads.
