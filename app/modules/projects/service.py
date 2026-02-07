from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.projects.schemas import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)


def list_projects(supabase: Client, tenant_id: str, user_id: str) -> list[ProjectResponse]:
    """Return projects the user is assigned to (member of), within the tenant."""
    members_r = supabase.schema(DB_SCHEMA).table("project_members").select("project_id").eq("user_id", user_id).execute()
    project_ids = [row["project_id"] for row in (members_r.data or [])]
    if not project_ids:
        return []
    r = (
        supabase.schema(DB_SCHEMA)
        .table("projects")
        .select("*")
        .eq("tenant_id", tenant_id)
        .in_("id", project_ids)
        .order("created_at", desc=True)
        .execute()
    )
    return [ProjectResponse(**row) for row in (r.data or [])]


def get_project(supabase: Client, project_id: str, tenant_id: str) -> ProjectResponse | None:
    r = supabase.schema(DB_SCHEMA).table("projects").select("*").eq("id", project_id).eq("tenant_id", tenant_id).maybe_single().execute()
    return ProjectResponse(**r.data) if r.data else None


def create_project(supabase: Client, tenant_id: str, payload: ProjectCreate, creator_user_id: str) -> ProjectResponse:
    row = {
        "tenant_id": tenant_id,
        "name": payload.name,
        "timezone": payload.timezone,
        "lat": payload.lat,
        "lng": payload.lng,
        "location": payload.location,
        "address": payload.address,
        "project_admin_user_id": payload.project_admin_user_id,
    }
    r = supabase.schema(DB_SCHEMA).table("projects").insert(row).execute()
    data = (r.data or [None])[0]
    if not data:
        raise ValueError("Insert did not return row")
    project_id = data.get("id")
    if project_id:
        supabase.schema(DB_SCHEMA).table("project_members").insert(
            {"project_id": project_id, "user_id": creator_user_id, "role": "admin"}
        ).execute()
    return ProjectResponse(**data)


def update_project(
    supabase: Client, project_id: str, tenant_id: str, payload: ProjectUpdate, *, full_replace: bool = False
) -> ProjectResponse:
    data = payload.model_dump(exclude_unset=not full_replace)
    if full_replace:
        data = {k: v for k, v in data.items() if k in ("name", "timezone", "lat", "lng", "location", "address", "project_admin_user_id")}
    if data:
        supabase.schema(DB_SCHEMA).table("projects").update(data).eq("id", project_id).eq("tenant_id", tenant_id).execute()
    proj = get_project(supabase, project_id, tenant_id)
    if not proj:
        raise ValueError("Project not found")
    return proj


def delete_project(supabase: Client, project_id: str, tenant_id: str) -> None:
    supabase.schema(DB_SCHEMA).table("projects").delete().eq("id", project_id).eq("tenant_id", tenant_id).execute()


def list_project_members(supabase: Client, project_id: str) -> list[ProjectMemberResponse]:
    r = supabase.schema(DB_SCHEMA).table("project_members").select("*").eq("project_id", project_id).order("created_at").execute()
    return [ProjectMemberResponse(**row) for row in (r.data or [])]


def add_project_member(supabase: Client, project_id: str, payload: ProjectMemberCreate) -> ProjectMemberResponse:
    row = {"project_id": project_id, "user_id": payload.user_id, "role": payload.role}
    r = supabase.schema(DB_SCHEMA).table("project_members").insert(row).execute()
    data = (r.data or [None])[0]
    if not data:
        raise ValueError("Insert did not return row")
    return ProjectMemberResponse(**data)


def update_project_member(supabase: Client, project_id: str, user_id: str, role: str) -> ProjectMemberResponse:
    r = supabase.schema(DB_SCHEMA).table("project_members").update({"role": role}).eq("project_id", project_id).eq("user_id", user_id).execute()
    row = (r.data or [None])[0]
    if not row:
        raise ValueError("Project member not found")
    return ProjectMemberResponse(**row)


def remove_project_member(supabase: Client, project_id: str, user_id: str) -> None:
    supabase.schema(DB_SCHEMA).table("project_members").delete().eq("project_id", project_id).eq("user_id", user_id).execute()
