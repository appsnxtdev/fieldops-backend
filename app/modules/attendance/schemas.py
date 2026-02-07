from pydantic import BaseModel


class AttendanceCheckIn(BaseModel):
    lat: float
    lng: float


class AttendanceCheckOut(BaseModel):
    lat: float
    lng: float


class AttendanceResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    date: str
    check_in_at: str | None = None
    check_out_at: str | None = None
    check_in_selfie_path: str | None = None
    check_out_selfie_path: str | None = None
    check_in_lat: float | None = None
    check_in_lng: float | None = None
    check_out_lat: float | None = None
    check_out_lng: float | None = None
