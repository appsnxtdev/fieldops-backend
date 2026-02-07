from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.dependencies import get_current_user, get_project_access, get_supabase_client
from app.core.permissions import CAN_LOG_ATTENDANCE, CAN_VIEW_ATTENDANCE
from app.modules.attendance.schemas import AttendanceResponse
from app.modules.attendance.service import check_in as do_check_in, check_out as do_check_out, list_attendance, upload_selfie
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
):
    user_id = current_user["id"]
    try:
        path = upload_selfie(supabase, project_id, user_id, date, "in", selfie)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        return do_check_in(supabase, project_id, user_id, date, lat, lng, path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
):
    user_id = current_user["id"]
    try:
        path = upload_selfie(supabase, project_id, user_id, date, "out", selfie)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        return do_check_out(supabase, project_id, user_id, date, lat, lng, path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}", response_model=list[AttendanceResponse])
def list_attendance_route(
    project_id: str,
    date: str,
    access: dict = Depends(get_project_access(CAN_VIEW_ATTENDANCE)),
    supabase: Client = Depends(get_supabase_client),
):
    return list_attendance(supabase, project_id, date)
