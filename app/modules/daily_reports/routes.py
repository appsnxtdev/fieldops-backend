from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.core.cache import CacheKeys, cache_delete, cache_get, cache_set, get_redis_client
from app.core.dependencies import get_current_user, get_project_access, get_project_access_query, get_supabase_client, get_tenant_id
from app.core.permissions import CAN_MANAGE_DAILY_REPORTS, CAN_VIEW_DAILY_REPORTS
from app.modules.daily_reports.schemas import (
    DailyReportDayAggregate,
    DailyReportEntryCreate,
    DailyReportEntryResponse,
    DailyReportListResponse,
    DailyReportResponse,
    DailyReportsByDateRangeResponse,
)
from app.modules.daily_reports.service import (
    append_entry,
    get_or_create_report,
    get_report_by_id,
    get_report_with_entries,
    list_all_entries_for_project_date,
    list_by_date_range,
    list_entries,
    list_recent_dates_with_reports,
    list_reports_for_project_date,
    upload_photo,
)
from supabase import Client

router = APIRouter()


@router.get("/recent-dates", response_model=list[str])
def recent_dates_route(
    project_id: str = Query(..., description="Project ID"),
    limit: int = Query(14, ge=1, le=30),
    access: dict = Depends(get_project_access_query(CAN_VIEW_DAILY_REPORTS)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    """Return report dates that have at least one report (most recent first), for default date in mobile."""
    pid = access["project_id"]
    key = CacheKeys.dr_recent_dates(pid)
    cached = cache_get(redis, key)
    if cached is not None:
        return cached
    result = list_recent_dates_with_reports(supabase, pid, limit)
    cache_set(redis, key, result, ttl=30)
    return result


@router.get("/by-date-range", response_model=DailyReportsByDateRangeResponse)
def by_date_range_route(
    project_id: str = Query(..., description="Project ID"),
    date_from: str = Query(..., description="Start date YYYY-MM-DD"),
    date_to: str = Query(..., description="End date YYYY-MM-DD"),
    access: dict = Depends(get_project_access_query(CAN_VIEW_DAILY_REPORTS)),
    supabase: Client = Depends(get_supabase_client),
):
    """Entries per date in range with user_id for attribution. Only dates with reports."""
    by_date = list_by_date_range(supabase, project_id, date_from, date_to)
    return DailyReportsByDateRangeResponse(by_date=by_date)


@router.get("/list", response_model=list[DailyReportListResponse])
def list_reports_route(
    project_id: str = Query(..., description="Project ID"),
    report_date: str = Query(..., description="Report date YYYY-MM-DD"),
    access: dict = Depends(get_project_access_query(CAN_VIEW_DAILY_REPORTS)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    """List all daily reports for a project on a given date (office view)."""
    pid = access["project_id"]
    key = CacheKeys.dr_list(pid, report_date)
    cached = cache_get(redis, key)
    if cached is not None:
        return [DailyReportListResponse(**r) for r in cached]
    rows = list_reports_for_project_date(supabase, pid, report_date)
    result = [DailyReportListResponse(**r) for r in rows]
    cache_set(redis, key, [r.model_dump() for r in result], ttl=30)
    return result


@router.get("/reports/{report_id}/entries", response_model=list[DailyReportEntryResponse])
def list_report_entries_by_id(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    """List entries for a report by id (office view). Access validated via report's project."""
    from app.core.dependencies import ensure_project_access

    report = get_report_by_id(supabase, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    project_id = str(report.get("project_id", ""))
    if not project_id:
        raise HTTPException(status_code=404, detail="Report not found")
    ensure_project_access(supabase, tenant_id, current_user["id"], project_id, CAN_VIEW_DAILY_REPORTS)
    return list_entries(supabase, report_id)


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
    redis=Depends(get_redis_client),
):
    role = access.get("role")
    if role == "admin":
        key = CacheKeys.dr_entries_all(project_id, report_date)
        cached = cache_get(redis, key)
        if cached is not None:
            return [DailyReportEntryResponse(**e) for e in cached]
        result = list_all_entries_for_project_date(supabase, project_id, report_date)
        cache_set(redis, key, [e.model_dump() if hasattr(e, "model_dump") else e for e in result], ttl=30)
        return result
    else:
        uid = current_user["id"]
        key = CacheKeys.dr_entries_member(project_id, uid, report_date)
        cached = cache_get(redis, key)
        if cached is not None:
            return [DailyReportEntryResponse(**e) for e in cached]
        report = get_or_create_report(supabase, project_id, uid, report_date)
        result = list_entries(supabase, report["id"])
        cache_set(redis, key, [e.model_dump() if hasattr(e, "model_dump") else e for e in result], ttl=30)
        return result


@router.post("/{project_id}/entries", response_model=DailyReportEntryResponse, status_code=201)
def add_report_entry(
    project_id: str,
    payload: DailyReportEntryCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_DAILY_REPORTS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    report = get_or_create_report(supabase, project_id, current_user["id"], payload.report_date)
    result = append_entry(supabase, report["id"], payload.type, payload.content, payload.sort_order)
    cache_delete(
        redis,
        CacheKeys.dr_recent_dates(project_id),
        CacheKeys.dr_list(project_id, payload.report_date),
        CacheKeys.dr_entries_all(project_id, payload.report_date),
    )
    return result


@router.post("/{project_id}/entries/photo", response_model=DailyReportEntryResponse, status_code=201)
async def add_report_photo(
    project_id: str,
    report_date: str = Form(...),
    sort_order: int = Form(0),
    photo: UploadFile = File(...),
    access: dict = Depends(get_project_access(CAN_MANAGE_DAILY_REPORTS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    report = get_or_create_report(supabase, project_id, current_user["id"], report_date)
    count = len(list_entries(supabase, report["id"]))
    path = upload_photo(supabase, project_id, current_user["id"], report_date, count, photo)
    result = append_entry(supabase, report["id"], "photo", path, sort_order)
    # Use report_date from Form field — NOT datetime.utcnow()
    cache_delete(
        redis,
        CacheKeys.dr_recent_dates(project_id),
        CacheKeys.dr_list(project_id, report_date),
        CacheKeys.dr_entries_all(project_id, report_date),
    )
    return result
