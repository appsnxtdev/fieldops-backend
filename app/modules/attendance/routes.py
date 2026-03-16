import csv
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.core.cache import CacheKeys, cache_delete, cache_get, cache_set, get_redis_client
from app.core.dependencies import get_current_user, get_project_access, get_supabase_client
from app.core.permissions import CAN_LOG_ATTENDANCE, CAN_VIEW_ATTENDANCE
from app.modules.attendance.schemas import AttendanceResponse
from app.modules.attendance.service import (
    check_in as do_check_in,
    check_out as do_check_out,
    list_attendance,
    list_attendance_in_range,
    upload_selfie,
)
from supabase import Client

router = APIRouter()


@router.post("/{project_id}/check-in", response_model=AttendanceResponse)
async def attendance_check_in(
    project_id: str,
    date: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    selfie: UploadFile = File(...),
    access: dict = Depends(get_project_access(CAN_LOG_ATTENDANCE)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    user_id = current_user["id"]
    try:
        path = upload_selfie(supabase, project_id, user_id, date, "in", selfie)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        result = do_check_in(supabase, project_id, user_id, date, lat, lng, path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    cache_delete(
        redis,
        CacheKeys.attendance(project_id, date),
        CacheKeys.dashboard(access["tenant_id"], user_id),
    )
    return result


@router.post("/{project_id}/check-out", response_model=AttendanceResponse)
async def attendance_check_out(
    project_id: str,
    date: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    selfie: UploadFile = File(...),
    access: dict = Depends(get_project_access(CAN_LOG_ATTENDANCE)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    user_id = current_user["id"]
    try:
        path = upload_selfie(supabase, project_id, user_id, date, "out", selfie)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        result = do_check_out(supabase, project_id, user_id, date, lat, lng, path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    cache_delete(
        redis,
        CacheKeys.attendance(project_id, date),
        CacheKeys.dashboard(access["tenant_id"], user_id),
    )
    return result


@router.get("/{project_id}", response_model=list[AttendanceResponse])
def list_attendance_route(
    project_id: str,
    date: str,
    access: dict = Depends(get_project_access(CAN_VIEW_ATTENDANCE)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    key = CacheKeys.attendance(project_id, date)
    cached = cache_get(redis, key)
    if cached is not None:
        return cached
    result = list_attendance(supabase, project_id, date)
    cache_set(redis, key, [r if isinstance(r, dict) else r.model_dump() for r in result], ttl=30)
    return result


@router.get("/{project_id}/export")
def export_attendance_route(
    project_id: str,
    from_date: str = Query(..., description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., description="End date YYYY-MM-DD"),
    access: dict = Depends(get_project_access(CAN_VIEW_ATTENDANCE)),
    supabase: Client = Depends(get_supabase_client),
):
    """Export attendance for a site as CSV (date range inclusive). Names and human-readable dates."""
    from app.modules.users.service import get_profiles_by_ids

    rows = list_attendance_in_range(supabase, project_id, from_date, to_date)
    user_ids = list({r.get("user_id") for r in rows if r.get("user_id")})
    profiles = get_profiles_by_ids(supabase, user_ids)
    profile_map = {p.id: p for p in profiles}

    def format_datetime(iso: str | None) -> str:
        if not iso:
            return ""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.strftime("%d %b %Y, %I:%M %p")
        except Exception:
            return iso or ""

    def member_name(uid: str | None) -> str:
        if not uid:
            return ""
        p = profile_map.get(uid)
        if p and (p.full_name or p.email):
            return (p.full_name or p.email or "").strip()
        return uid[:8] if uid else ""

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "member_name", "check_in_at", "check_out_at"])
    for r in rows:
        w.writerow([
            r.get("date") or "",
            member_name(r.get("user_id")),
            format_datetime(r.get("check_in_at")),
            format_datetime(r.get("check_out_at")),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{project_id}_{from_date}_{to_date}.csv"},
    )
