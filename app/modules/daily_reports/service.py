import logging

from fastapi import UploadFile
from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.daily_reports.schemas import (
    DailyReportDayAggregate,
    DailyReportEntryResponse,
    DailyReportEntryWithUser,
    DailyReportResponse,
)

DAILY_REPORTS_BUCKET = "daily_reports"
log = logging.getLogger(__name__)


def _ensure_bucket(supabase: Client, bucket: str) -> None:
    try:
        buckets = supabase.storage.list_buckets()
        names = [b.get("name") for b in (buckets or []) if isinstance(b, dict)]
        if bucket not in names:
            supabase.storage.create_bucket(bucket, options={"public": False})
            log.info("Created storage bucket: %s", bucket)
    except Exception as e:
        log.warning("Could not ensure bucket %s: %s", bucket, e)


def get_or_create_report(supabase: Client, project_id: str, user_id: str, report_date: str) -> dict:
    r = (
        supabase.schema(DB_SCHEMA).table("daily_reports")
        .select("*")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .eq("report_date", report_date)
        .maybe_single()
        .execute()
    )
    if r is not None and getattr(r, "data", None) not in (None, []):
        return r.data if isinstance(r.data, dict) else (r.data or [{}])[0]
    ins = (
        supabase.schema(DB_SCHEMA).table("daily_reports")
        .insert({"project_id": project_id, "user_id": user_id, "report_date": report_date})
        .execute()
    )
    data = (ins.data or [None])[0] if ins else None
    if not data:
        raise RuntimeError("Failed to create daily report")
    return data


def upload_photo(supabase: Client, project_id: str, user_id: str, report_date: str, index: int, file: UploadFile) -> str:
    _ensure_bucket(supabase, DAILY_REPORTS_BUCKET)
    path = f"{project_id}/{user_id}/{report_date}_{index}.jpg"
    file.file.seek(0)
    content = file.file.read()
    if not content:
        raise ValueError("Photo file is empty")
    opts = {"content-type": file.content_type or "image/jpeg", "upsert": "true"}
    supabase.storage.from_(DAILY_REPORTS_BUCKET).upload(path, content, file_options=opts)
    return path


def append_entry(supabase: Client, daily_report_id: str, type_: str, content: str, sort_order: int = 0) -> DailyReportEntryResponse:
    r = (
        supabase.schema(DB_SCHEMA).table("daily_report_entries")
        .insert({"daily_report_id": daily_report_id, "type": type_, "content": content, "sort_order": sort_order})
        .execute()
    )
    data = (r.data or [None])[0] if r else None
    if not data:
        raise RuntimeError("Failed to create daily report entry")
    return DailyReportEntryResponse(**data)


def list_entries(supabase: Client, daily_report_id: str) -> list[DailyReportEntryResponse]:
    r = (
        supabase.schema(DB_SCHEMA).table("daily_report_entries")
        .select("*")
        .eq("daily_report_id", daily_report_id)
        .order("sort_order")
        .order("created_at")
        .execute()
    )
    return [DailyReportEntryResponse(**row) for row in (r.data or [])]


def get_report_with_entries(supabase: Client, project_id: str, user_id: str, report_date: str) -> DailyReportResponse | None:
    report = get_or_create_report(supabase, project_id, user_id, report_date)
    if not report:
        return None
    return DailyReportResponse(**report)


def get_report_by_id(supabase: Client, report_id: str) -> dict | None:
    r = (
        supabase.schema(DB_SCHEMA).table("daily_reports")
        .select("*")
        .eq("id", report_id)
        .maybe_single()
        .execute()
    )
    if not r.data:
        return None
    return r.data[0] if isinstance(r.data, list) else r.data


def list_reports_for_project_date(supabase: Client, project_id: str, report_date: str) -> list[dict]:
    """List all daily reports for a project on a given date (for office view)."""
    r = (
        supabase.schema(DB_SCHEMA).table("daily_reports")
        .select("id, project_id, user_id, report_date, created_at")
        .eq("project_id", project_id)
        .eq("report_date", report_date)
        .order("created_at")
        .execute()
    )
    return list(r.data or [])


def list_all_entries_for_project_date(
    supabase: Client, project_id: str, report_date: str
) -> list[DailyReportEntryResponse]:
    """List entries from all daily reports for a project on a given date (admin view)."""
    reports = list_reports_for_project_date(supabase, project_id, report_date)
    all_entries: list[DailyReportEntryResponse] = []
    for report in reports:
        all_entries.extend(list_entries(supabase, report["id"]))
    all_entries.sort(key=lambda e: (e.sort_order, e.created_at or ""))
    return all_entries


def list_reports_for_project_date_range(
    supabase: Client, project_id: str, date_from: str, date_to: str
) -> list[dict]:
    """List all daily reports for a project in date range (inclusive)."""
    r = (
        supabase.schema(DB_SCHEMA)
        .table("daily_reports")
        .select("id, project_id, user_id, report_date, created_at")
        .eq("project_id", project_id)
        .gte("report_date", date_from)
        .lte("report_date", date_to)
        .order("report_date", desc=True)
        .order("created_at")
        .execute()
    )
    return list(r.data or [])


def list_entries_with_user(
    supabase: Client, report: dict
) -> list[DailyReportEntryWithUser]:
    """List entries for a report with user_id attached."""
    entries = list_entries(supabase, report["id"])
    user_id = report.get("user_id", "")
    return [
        DailyReportEntryWithUser(**{**e.model_dump(), "user_id": user_id})
        for e in entries
    ]


def list_by_date_range(
    supabase: Client, project_id: str, date_from: str, date_to: str
) -> dict[str, DailyReportDayAggregate]:
    """Entries per date in range (photos and notes with user_id). Only dates with at least one report."""
    reports = list_reports_for_project_date_range(
        supabase, project_id, date_from, date_to
    )
    by_date: dict[str, list[DailyReportEntryWithUser]] = {}
    for report in reports:
        report_date = report.get("report_date")
        if not report_date:
            continue
        date_str = str(report_date)
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].extend(list_entries_with_user(supabase, report))
    result: dict[str, DailyReportDayAggregate] = {}
    for date_str, entries in by_date.items():
        entries.sort(key=lambda e: (e.sort_order, e.created_at or ""))
        photos = [e for e in entries if e.type == "photo"]
        notes = [e for e in entries if e.type == "note"]
        result[date_str] = DailyReportDayAggregate(photos=photos, notes=notes)
    return result


def list_recent_dates_with_reports(
    supabase: Client, project_id: str, limit: int = 14
) -> list[str]:
    """Return report_date values that have at least one report, most recent first (for default date pick)."""
    r = (
        supabase.schema(DB_SCHEMA).table("daily_reports")
        .select("report_date")
        .eq("project_id", project_id)
        .order("report_date", desc=True)
        .limit(limit * 2)
        .execute()
    )
    seen: set[str] = set()
    out: list[str] = []
    for row in (r.data or []):
        d = row.get("report_date") if isinstance(row, dict) else None
        if d and d not in seen:
            seen.add(d)
            out.append(str(d))
            if len(out) >= limit:
                break
    return out
