from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.dependencies import get_current_user, get_project_access, get_supabase_client
from app.core.permissions import CAN_MANAGE_DAILY_REPORTS, CAN_VIEW_DAILY_REPORTS
from app.modules.daily_reports.schemas import DailyReportEntryCreate, DailyReportEntryResponse, DailyReportResponse
from app.modules.daily_reports.service import (
    append_entry,
    get_or_create_report,
    get_report_with_entries,
    list_entries,
    upload_photo,
)
from supabase import Client

router = APIRouter()


@router.get("/{project_id}", response_model=DailyReportResponse)
def get_my_report(
    project_id: str,
    report_date: str,
    access: dict = Depends(get_project_access(CAN_VIEW_DAILY_REPORTS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    report = get_report_with_entries(supabase, project_id, current_user["id"], report_date)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{project_id}/entries", response_model=list[DailyReportEntryResponse])
def list_report_entries(
    project_id: str,
    report_date: str,
    access: dict = Depends(get_project_access(CAN_VIEW_DAILY_REPORTS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    report = get_or_create_report(supabase, project_id, current_user["id"], report_date)
    return list_entries(supabase, report["id"])


@router.post("/{project_id}/entries", response_model=DailyReportEntryResponse, status_code=201)
def add_report_entry(
    project_id: str,
    payload: DailyReportEntryCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_DAILY_REPORTS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    report = get_or_create_report(supabase, project_id, current_user["id"], payload.report_date)
    return append_entry(supabase, report["id"], payload.type, payload.content, payload.sort_order)


@router.post("/{project_id}/entries/photo", response_model=DailyReportEntryResponse, status_code=201)
async def add_report_photo(
    project_id: str,
    report_date: str = Form(...),
    sort_order: int = Form(0),
    photo: UploadFile = File(...),
    access: dict = Depends(get_project_access(CAN_MANAGE_DAILY_REPORTS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    report = get_or_create_report(supabase, project_id, current_user["id"], report_date)
    count = len(list_entries(supabase, report["id"]))
    path = upload_photo(supabase, project_id, current_user["id"], report_date, count, photo)
    return append_entry(supabase, report["id"], "photo", path, sort_order)
