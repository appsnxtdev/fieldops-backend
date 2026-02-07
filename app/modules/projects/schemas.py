from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    timezone: str = "Asia/Kolkata"
    lat: float | None = None
    lng: float | None = None
    location: str | None = None
    address: str | None = None
    project_admin_user_id: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None
    lat: float | None = None
    lng: float | None = None
    location: str | None = None
    address: str | None = None
    project_admin_user_id: str | None = None


class ProjectResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    timezone: str
    lat: float | None = None
    lng: float | None = None
    location: str | None = None
    address: str | None = None
    project_admin_user_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProjectMemberCreate(BaseModel):
    user_id: str
    role: str  # admin | member | viewer


class ProjectMemberUpdate(BaseModel):
    role: str


class ProjectMemberResponse(BaseModel):
    project_id: str
    user_id: str
    role: str
    created_at: str | None = None


class ProjectMyAccessResponse(BaseModel):
    role: str  # admin | member | viewer
