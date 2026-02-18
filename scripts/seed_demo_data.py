#!/usr/bin/env python3
"""
Seed demo data for FieldOps: one tenant, one owner, N sites, 3 supervisors per site,
with attendance, tasks, daily reports, expense, and materials. Uses Supabase Auth + fieldops schema.
Run with: SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python scripts/seed_demo_data.py
Optional: SEED_DRY_RUN=1 (no writes), SEED_CLEANUP=1 (delete seed data), SEED_N_SITES=3, SEED_DAYS_ATTENDANCE=14, SEED_DAYS_REPORTS=7.
"""
from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# Load .env from backend root if present
try:
    from dotenv import load_dotenv
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass

DB_SCHEMA = "fieldops"
DEMO_EMAIL_DOMAIN = "fieldops-demo.local"
DEFAULT_PASSWORD = "DemoPassword123!"
MATERIAL_UNITS = ("kg", "L", "pieces", "m", "m²", "bags", "tonnes", "cubic m", "boxes", "rolls")

# Realistic Indian names for owner and supervisors
OWNER_NAME = "Ramesh Kumar"
SUPERVISOR_NAMES = [
    "Arun Singh", "Priya Sharma", "Vikram Patel",
    "Sneha Reddy", "Rajesh Nair", "Kavita Desai",
    "Amit Joshi", "Anita Iyer", "Suresh Menon",
]

PROJECT_NAMES = [
    "Block A – Phase 2",
    "Tower B Site",
    "Warehouse Expansion",
]

PROJECT_ADDRESSES = [
    "Plot 12, Sector 5, Industrial Area, Bangalore 560001",
    "Site Office, NH 48, Tumakuru Road, Bangalore 560073",
    "Warehouse Zone, Peenya Industrial Area, Bangalore 560058",
]

# Coords near Bangalore (slightly different per project)
PROJECT_COORDS = [
    (12.9716, 77.5946),
    (13.0045, 77.5821),
    (13.0332, 77.5123),
]

TASK_TITLES = [
    "Foundation inspection", "Safety audit", "Material receipt verification",
    "Daily site log", "Slab casting check", "Labour attendance",
    "Quality check – columns", "Bar bending schedule review", "Shuttering inspection",
]

DAILY_REPORT_NOTES = [
    "Site cleared for casting. Labour count 25.",
    "Delivery received: 50 bags cement. Stored in shed.",
    "Safety briefing conducted. All PPE checked.",
    "Progress on column work – 4 columns completed.",
    "Minor delay due to rain. Resumed by 11:00.",
]

EXPENSE_CREDIT_NOTES = ["Advance from HO", "Budget allocation", "Monthly release"]
EXPENSE_DEBIT_NOTES = ["Cement purchase", "Labour payment", "Equipment hire", "Misc site expenses"]

MASTER_MATERIALS = [
    ("Cement", "bags"),
    ("Sand", "tonnes"),
    ("Steel", "kg"),
    ("Aggregate", "tonnes"),
    ("Bricks", "pieces"),
    ("Paint", "L"),
    ("Cement Primer", "boxes"),
    ("Tiles", "pieces"),
]


def get_env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name)
    if v is not None:
        return v.strip()
    if default is not None:
        return default
    logging.error("Missing required env: %s", name)
    sys.exit(1)


def create_supabase_client():
    url = get_env("SUPABASE_URL")
    key = get_env("SUPABASE_SERVICE_ROLE_KEY")
    from supabase import create_client
    return create_client(url, key)


def create_auth_user(supabase, email: str, password: str, full_name: str, tenant_id: str, *, dry_run: bool):
    if dry_run:
        return str(uuid4())
    admin = getattr(supabase.auth, "admin", None)
    if not admin:
        raise RuntimeError("Supabase auth.admin not available (need service role key)")
    # create_user typically: email, password, email_confirm=True, app_metadata={}
    try:
        result = admin.create_user(
            dict(
                email=email,
                password=password,
                email_confirm=True,
                app_metadata={"tenant_id": str(tenant_id)},
                user_metadata={"full_name": full_name},
            )
        )
    except TypeError:
        result = admin.create_user(
            email=email,
            password=password,
            email_confirm=True,
            app_metadata={"tenant_id": str(tenant_id)},
            user_metadata={"full_name": full_name},
        )
    user = result.user if hasattr(result, "user") else (result if not hasattr(result, "data") else getattr(result, "data", result))
    if hasattr(user, "id"):
        return str(user.id)
    if isinstance(user, dict):
        return str(user.get("id", ""))
    raise RuntimeError("create_user did not return user id")


def seed(
    *,
    dry_run: bool = False,
    cleanup: bool = False,
    n_sites: int = 3,
    days_attendance: int = 14,
    days_reports: int = 7,
):
    if cleanup and not dry_run:
        return run_cleanup(create_supabase_client())
    if dry_run:
        _dry_run_print(n_sites, days_attendance, days_reports)
        return

    supabase = create_supabase_client()
    tenant_id = str(uuid4())
    owner_email = f"owner@{DEMO_EMAIL_DOMAIN}"
    password = get_env("SEED_PASSWORD", DEFAULT_PASSWORD)

    # 1) Create owner + supervisors in Auth and fieldops
    log.info("Tenant: %s", tenant_id)
    owner_id = create_auth_user(supabase, owner_email, password, OWNER_NAME, tenant_id, dry_run=False)
    log.info("  Auth user: %s (%s)", owner_email, OWNER_NAME)
    tbl = supabase.schema(DB_SCHEMA).table
    tbl("profiles").insert({"id": owner_id, "email": owner_email, "full_name": OWNER_NAME}).execute()
    log.info("  Profile: %s", owner_email)
    tbl("tenant_members").insert({"tenant_id": tenant_id, "user_id": owner_id, "role": "org_admin"}).execute()
    log.info("  Tenant member: %s (org_admin)", owner_email)

    supervisors = []
    for site_idx in range(n_sites):
        for k in range(3):
            idx = site_idx * 3 + k
            name = SUPERVISOR_NAMES[idx % len(SUPERVISOR_NAMES)]
            email = f"supervisor-{site_idx}-{k+1}@{DEMO_EMAIL_DOMAIN}"
            uid = create_auth_user(supabase, email, password, name, tenant_id, dry_run=False)
            log.info("  Auth user: %s (%s)", email, name)
            tbl("profiles").insert({"id": uid, "email": email, "full_name": name}).execute()
            log.info("  Profile: %s", email)
            tbl("tenant_members").insert({"tenant_id": tenant_id, "user_id": uid, "role": "member"}).execute()
            log.info("  Tenant member: %s (member)", email)
            supervisors.append({"id": uid, "email": email, "full_name": name})
    all_supervisor_ids = [s["id"] for s in supervisors]

    # 2) Projects and project_members
    log.info("Projects and members:")
    projects = []
    for i in range(n_sites):
        name = PROJECT_NAMES[i % len(PROJECT_NAMES)]
        lat, lng = PROJECT_COORDS[i % len(PROJECT_COORDS)]
        addr = PROJECT_ADDRESSES[i % len(PROJECT_ADDRESSES)]
        site_sups = supervisors[i * 3 : (i + 1) * 3]
        admin_id = site_sups[0]["id"]
        r = tbl("projects").insert({
            "tenant_id": tenant_id,
            "name": name,
            "timezone": "Asia/Kolkata",
            "lat": lat,
            "lng": lng,
            "address": addr,
            "location": name,
            "project_admin_user_id": admin_id,
        }).execute()
        proj = (r.data or [None])[0]
        if not proj:
            raise RuntimeError("Project insert failed")
        proj_id = proj["id"]
        projects.append({"id": proj_id, "name": name, "lat": lat, "lng": lng, "supervisors": site_sups})
        log.info("  Project: %s", name)
        for j, s in enumerate(site_sups):
            tbl("project_members").insert({
                "project_id": proj_id,
                "user_id": s["id"],
                "role": "admin" if j == 0 else "member",
            }).execute()
            log.info("    Member: %s (%s)", s["email"], "admin" if j == 0 else "member")

    # 3) Task statuses and tasks per project
    today = date.today()
    log.info("Task statuses and tasks:")
    for proj in projects:
        proj_id = proj["id"]
        proj_name = proj["name"]
        sups = [s["id"] for s in proj["supervisors"]]
        status_ids = {}
        for order, label in enumerate(["To Do", "In Progress", "Done"]):
            r = tbl("project_task_statuses").insert({
                "project_id": proj_id,
                "name": label,
                "sort_order": order,
            }).execute()
            row = (r.data or [None])[0]
            if row:
                status_ids[label] = row["id"]
        log.info("  [%s] Statuses: To Do, In Progress, Done", proj_name)
        task_count = 0
        update_count = 0
        for _ in range(random.randint(6, 12)):
            status_name = random.choice(list(status_ids.keys()))
            title = random.choice(TASK_TITLES)
            due = today + timedelta(days=random.randint(-5, 10))
            due_at = datetime(due.year, due.month, due.day, 17, 0, 0, tzinfo=timezone.utc).isoformat()
            r = tbl("tasks").insert({
                "project_id": proj_id,
                "title": title,
                "description": None,
                "status_id": status_ids.get(status_name),
                "assignee_id": random.choice(sups),
                "created_by": random.choice(sups),
                "due_at": due_at,
            }).execute()
            task = (r.data or [None])[0]
            task_count += 1
            if task and random.random() < 0.4:
                tbl("task_updates").insert({
                    "task_id": task["id"],
                    "project_id": proj_id,
                    "author_id": random.choice(sups),
                    "note": random.choice(DAILY_REPORT_NOTES),
                }).execute()
                update_count += 1
        log.info("  [%s] Tasks: %d (with %d task updates)", proj_name, task_count, update_count)

    # 4) Attendance (last N days, check-in/out near project)
    log.info("Attendance:")
    for proj in projects:
        proj_id, lat, lng, sups = proj["id"], proj["lat"], proj["lng"], proj["supervisors"]
        count = 0
        for d in range(days_attendance):
            dte = today - timedelta(days=d)
            for s in sups:
                off_lat = random.uniform(-0.0025, 0.0025)
                off_lng = random.uniform(-0.0025, 0.0025)
                check_in = datetime(dte.year, dte.month, dte.day, 8, random.randint(0, 30), 0, tzinfo=timezone.utc)
                check_out = datetime(dte.year, dte.month, dte.day, 17, random.randint(0, 45), 0, tzinfo=timezone.utc)
                tbl("attendance").insert({
                    "project_id": proj_id,
                    "user_id": s["id"],
                    "date": dte.isoformat(),
                    "check_in_at": check_in.isoformat(),
                    "check_out_at": check_out.isoformat(),
                    "check_in_lat": lat + off_lat,
                    "check_in_lng": lng + off_lng,
                    "check_out_lat": lat + off_lat,
                    "check_out_lng": lng + off_lng,
                }).execute()
                count += 1
        log.info("  [%s] %d attendance records (last %d days × 3 supervisors)", proj["name"], count, days_attendance)

    # 5) Daily reports and entries
    log.info("Daily reports and entries:")
    for proj in projects:
        proj_id = proj["id"]
        proj_name = proj["name"]
        sups = proj["supervisors"]
        report_count = 0
        entry_count = 0
        for d in range(days_reports):
            dte = today - timedelta(days=d)
            for s in sups:
                r = tbl("daily_reports").insert({
                    "project_id": proj_id,
                    "user_id": s["id"],
                    "report_date": dte.isoformat(),
                }).execute()
                report = (r.data or [None])[0]
                report_count += 1
                if report:
                    n_entries = min(3, len(DAILY_REPORT_NOTES))
                    for idx, note in enumerate(random.sample(DAILY_REPORT_NOTES, n_entries)):
                        tbl("daily_report_entries").insert({
                            "daily_report_id": report["id"],
                            "type": "note",
                            "content": note,
                            "sort_order": idx,
                        }).execute()
                        entry_count += 1
        log.info("  [%s] %d reports, %d entries", proj_name, report_count, entry_count)

    # 6) Expense
    log.info("Expense transactions:")
    receipt_placeholder = "seed/receipt_placeholder.pdf"
    for proj in projects:
        proj_id = proj["id"]
        proj_name = proj["name"]
        sups = [s["id"] for s in proj["supervisors"]]
        for _ in range(3):
            amt = round(random.uniform(50000, 200000), 2)
            notes = random.choice(EXPENSE_CREDIT_NOTES)
            tbl("expense_transactions").insert({
                "project_id": proj_id,
                "type": "credit",
                "amount": amt,
                "notes": notes,
                "created_by": random.choice(sups),
            }).execute()
            log.info("  [%s] Credit: %.2f – %s", proj_name, amt, notes)
        for _ in range(4):
            amt = round(random.uniform(5000, 75000), 2)
            notes = random.choice(EXPENSE_DEBIT_NOTES)
            tbl("expense_transactions").insert({
                "project_id": proj_id,
                "type": "debit",
                "amount": amt,
                "receipt_storage_path": receipt_placeholder,
                "notes": notes,
                "created_by": random.choice(sups),
            }).execute()
            log.info("  [%s] Debit: %.2f – %s", proj_name, amt, notes)

    # 7) Master materials (tenant) + materials per project + ledger
    log.info("Master materials (catalog):")
    master_ids = []
    for name, unit in MASTER_MATERIALS:
        r = tbl("master_materials").insert({"tenant_id": tenant_id, "name": name, "unit": unit}).execute()
        row = (r.data or [None])[0]
        if row:
            master_ids.append((row["id"], name, unit))
            log.info("  %s (%s)", name, unit)
    materials_summary = []
    log.info("Project materials and ledger:")
    for proj in projects:
        proj_id = proj["id"]
        proj_name = proj["name"]
        sups = [s["id"] for s in proj["supervisors"]]
        material_rows = []
        for mid, name, unit in master_ids:
            r = tbl("materials").insert({
                "project_id": proj_id,
                "name": name,
                "unit": unit,
                "master_material_id": mid,
            }).execute()
            row = (r.data or [None])[0]
            if row:
                material_rows.append(row)
                materials_summary.append((proj_name, name, unit))
                log.info("  [%s] Material: %s (%s)", proj_name, name, unit)
        for pname, punit in [("Shuttering Oil", "L"), ("Wire Mesh", "m²"), ("Adhesive", "bags")]:
            r = tbl("materials").insert({
                "project_id": proj_id,
                "name": pname,
                "unit": punit,
                "master_material_id": None,
            }).execute()
            row = (r.data or [None])[0]
            if row:
                material_rows.append(row)
                materials_summary.append((proj_name, pname, punit))
                log.info("  [%s] Material: %s (%s)", proj_name, pname, punit)
        in_count = out_count = 0
        for mat in material_rows:
            n_in = random.randint(3, 6)
            n_out = random.randint(2, 5)
            for _ in range(n_in):
                qty = round(random.uniform(20, 250), 2)
                tbl("material_ledger").insert({
                    "material_id": mat["id"],
                    "type": "in",
                    "quantity": qty,
                    "notes": "Stock receipt / delivery",
                    "created_by": random.choice(sups),
                }).execute()
                in_count += 1
            for _ in range(n_out):
                qty = round(random.uniform(5, 100), 2)
                tbl("material_ledger").insert({
                    "material_id": mat["id"],
                    "type": "out",
                    "quantity": qty,
                    "notes": "Site use / issued to work",
                    "created_by": random.choice(sups),
                }).execute()
                out_count += 1
        log.info("  [%s] Ledger: %d in, %d out", proj_name, in_count, out_count)

    # Summary
    log.info("--- Seed complete ---")
    log.info("Tenant ID: %s", tenant_id)
    log.info("Owner login: %s | Password: %s", owner_email, password)
    log.info("Projects: %s", [p["name"] for p in projects])
    log.info("Supervisors: %s", [s["email"] for s in supervisors])
    log.info("Materials: %d master (catalog), %d project materials with ledger in/out", len(master_ids), len(materials_summary))
    log.info("Log in as owner to see all sites in the dashboard.")


def _dry_run_print(n_sites: int, days_attendance: int, days_reports: int):
    n_sup = 3 * n_sites
    log.info("--- Dry run (no writes) ---")
    log.info("Would create: 1 tenant, 1 owner, %d supervisors, %d projects", n_sup, n_sites)
    log.info("Attendance: last %d days per supervisor per project", days_attendance)
    log.info("Daily reports: last %d days with note entries", days_reports)
    log.info("Plus: task statuses & tasks, task_updates, expense credits/debits,")
    log.info("      master_materials (catalog), materials per project, material_ledger (in/out)")


def run_cleanup(supabase):
    tbl = supabase.schema(DB_SCHEMA).table
    # Find tenant_id by any profile with demo email
    r = supabase.schema(DB_SCHEMA).table("profiles").select("id").ilike("email", f"%@{DEMO_EMAIL_DOMAIN}").limit(1).execute()
    if not r.data:
        log.info("No seed data found (no @fieldops-demo.local profiles).")
        return
    user_id = r.data[0]["id"]
    r2 = tbl("tenant_members").select("tenant_id").eq("user_id", user_id).limit(1).execute()
    if not r2.data:
        log.info("No tenant_members for demo user.")
        return
    tenant_id = r2.data[0]["tenant_id"]
    # Collect all user_ids for this tenant before deleting tenant_members
    tm_r = tbl("tenant_members").select("user_id").eq("tenant_id", tenant_id).execute()
    demo_user_ids = [row["user_id"] for row in (tm_r.data or [])]
    # Get project ids
    proj_r = tbl("projects").select("id").eq("tenant_id", tenant_id).execute()
    project_ids = [row["id"] for row in (proj_r.data or [])]
    # Delete in FK order
    for pid in project_ids:
        tbl("task_updates").delete().eq("project_id", pid).execute()
        tbl("tasks").delete().eq("project_id", pid).execute()
        tbl("project_task_statuses").delete().eq("project_id", pid).execute()
        tbl("attendance").delete().eq("project_id", pid).execute()
        dr_r = tbl("daily_reports").select("id").eq("project_id", pid).execute()
        for dr in dr_r.data or []:
            tbl("daily_report_entries").delete().eq("daily_report_id", dr["id"]).execute()
        tbl("daily_reports").delete().eq("project_id", pid).execute()
        tbl("expense_transactions").delete().eq("project_id", pid).execute()
        mat_r = tbl("materials").select("id").eq("project_id", pid).execute()
        for m in mat_r.data or []:
            tbl("material_ledger").delete().eq("material_id", m["id"]).execute()
        tbl("materials").delete().eq("project_id", pid).execute()
        tbl("project_members").delete().eq("project_id", pid).execute()
    tbl("projects").delete().eq("tenant_id", tenant_id).execute()
    tbl("master_materials").delete().eq("tenant_id", tenant_id).execute()
    tbl("tenant_members").delete().eq("tenant_id", tenant_id).execute()
    for uid in demo_user_ids:
        tbl("profiles").delete().eq("id", uid).execute()
        try:
            supabase.auth.admin.delete_user(uid)
        except Exception:
            pass
    log.info("Cleanup done for tenant %s", tenant_id)


def main():
    parser = argparse.ArgumentParser(description="Seed FieldOps demo data")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created, no writes")
    parser.add_argument("--cleanup", action="store_true", help="Delete seed data (demo tenant and users)")
    parser.add_argument("--sites", type=int, default=None, help="Number of sites (default from SEED_N_SITES or 3)")
    parser.add_argument("--days-attendance", type=int, default=None)
    parser.add_argument("--days-reports", type=int, default=None)
    args = parser.parse_args()
    n_sites = args.sites if args.sites is not None else int(get_env("SEED_N_SITES", "3"))
    days_attendance = args.days_attendance if args.days_attendance is not None else int(get_env("SEED_DAYS_ATTENDANCE", "14"))
    days_reports = args.days_reports if args.days_reports is not None else int(get_env("SEED_DAYS_REPORTS", "7"))
    dry_run = args.dry_run or (get_env("SEED_DRY_RUN", "0").strip() == "1")
    cleanup = args.cleanup or (get_env("SEED_CLEANUP", "0").strip() == "1")
    seed(dry_run=dry_run, cleanup=cleanup, n_sites=n_sites, days_attendance=days_attendance, days_reports=days_reports)


if __name__ == "__main__":
    main()
