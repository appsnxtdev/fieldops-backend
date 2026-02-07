from fastapi import UploadFile
from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.daily_reports.schemas import DailyReportEntryResponse, DailyReportResponse


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
    path = f"daily_reports/{project_id}/{user_id}/{report_date}_{index}.jpg"
    content = file.file.read()
    supabase.storage.from_("daily_reports").upload(path, content, file_options={"content-type": file.content_type or "image/jpeg"})
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
