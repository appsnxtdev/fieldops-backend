from fastapi import UploadFile
from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.attendance.geo import haversine_meters
from app.modules.attendance.schemas import AttendanceResponse


# Allow GPS/emulator variance; exact match can still show small distance due to float precision
RADIUS_METERS = 500


def _check_distance(project_lat: float | None, project_lng: float | None, lat: float, lng: float) -> bool:
    if project_lat is None or project_lng is None:
        return True
    try:
        plat = float(project_lat)
        plng = float(project_lng)
    except (TypeError, ValueError):
        return True
    return haversine_meters(plat, plng, lat, lng) <= RADIUS_METERS


def get_project_location(supabase: Client, project_id: str) -> tuple[float | None, float | None]:
    r = supabase.schema(DB_SCHEMA).table("projects").select("lat, lng").eq("id", project_id).maybe_single().execute()
    if not r or not r.data:
        return None, None
    raw_lat, raw_lng = r.data.get("lat"), r.data.get("lng")
    if raw_lat is None or raw_lng is None:
        return None, None
    try:
        return float(raw_lat), float(raw_lng)
    except (TypeError, ValueError):
        return None, None


def upload_selfie(supabase: Client, project_id: str, user_id: str, date: str, kind: str, file: UploadFile) -> str:
    path = f"attendance/{project_id}/{user_id}/{date}_{kind}.jpg"
    content = file.file.read()
    supabase.storage.from_("attendance").upload(path, content, file_options={"content-type": file.content_type or "image/jpeg"})
    return path


def get_or_create_attendance(supabase: Client, project_id: str, user_id: str, date: str) -> dict:
    r = supabase.schema(DB_SCHEMA).table("attendance").select("*").eq("project_id", project_id).eq("user_id", user_id).eq("date", date).maybe_single().execute()
    if r and r.data:
        return r.data
    ins = supabase.schema(DB_SCHEMA).table("attendance").insert({"project_id": project_id, "user_id": user_id, "date": date}).execute()
    data = (ins.data or [None])[0] if ins else None
    if not data:
        raise ValueError("Failed to create attendance record")
    return data


def check_in(supabase: Client, project_id: str, user_id: str, date: str, lat: float, lng: float, selfie_path: str) -> AttendanceResponse:
    proj_lat, proj_lng = get_project_location(supabase, project_id)
    if not _check_distance(proj_lat, proj_lng, lat, lng):
        raise ValueError("Outside allowed radius (500m from project location)")
    row = get_or_create_attendance(supabase, project_id, user_id, date)
    if row.get("check_in_at"):
        raise ValueError("Already checked in")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    up = (
        supabase.schema(DB_SCHEMA).table("attendance")
        .update({
            "check_in_at": now,
            "check_in_selfie_path": selfie_path,
            "check_in_lat": lat,
            "check_in_lng": lng,
            "updated_at": now,
        })
        .eq("id", row["id"])
        .execute()
    )
    data = (up.data or [None])[0] if up else None
    if not data:
        raise ValueError("Failed to update attendance")
    return AttendanceResponse(**data)


def check_out(supabase: Client, project_id: str, user_id: str, date: str, lat: float, lng: float, selfie_path: str) -> AttendanceResponse:
    proj_lat, proj_lng = get_project_location(supabase, project_id)
    if not _check_distance(proj_lat, proj_lng, lat, lng):
        raise ValueError("Outside allowed radius (500m from project location)")
    r = supabase.schema(DB_SCHEMA).table("attendance").select("*").eq("project_id", project_id).eq("user_id", user_id).eq("date", date).maybe_single().execute()
    if not r or not r.data:
        raise ValueError("No check-in found")
    if not r.data.get("check_in_at"):
        raise ValueError("Must check in first")
    if r.data.get("check_out_at"):
        raise ValueError("Already checked out")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    up = (
        supabase.schema(DB_SCHEMA).table("attendance")
        .update({
            "check_out_at": now,
            "check_out_selfie_path": selfie_path,
            "check_out_lat": lat,
            "check_out_lng": lng,
            "updated_at": now,
        })
        .eq("id", r.data["id"])
        .execute()
    )
    data = (up.data or [None])[0] if up else None
    if not data:
        raise ValueError("Failed to update attendance")
    return AttendanceResponse(**data)


def list_attendance(supabase: Client, project_id: str, date: str) -> list[AttendanceResponse]:
    r = supabase.schema(DB_SCHEMA).table("attendance").select("*").eq("project_id", project_id).eq("date", date).order("check_in_at").execute()
    return [AttendanceResponse(**row) for row in (r.data or [])] if r else []
