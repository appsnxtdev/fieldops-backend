from datetime import datetime, timezone

from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.projects.schemas import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectUpdateNoteResponse,
    UserBasicInfo,
)


def list_projects(
    supabase: Client, tenant_id: str, user_id: str, *, tenant_role: str | None = None
) -> list[ProjectResponse]:
    """Return projects for the user. If tenant_role is org_admin or demo, return all tenant projects; else projects user is a member of."""
    if tenant_role in ("org_admin", "demo"):
        r = (
            supabase.schema(DB_SCHEMA)
            .table("projects")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
        return [ProjectResponse(**row) for row in (r.data or [])]
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


def get_user_admin_projects(
    supabase: Client, tenant_id: str, user_id: str
) -> list[ProjectResponse]:
    """
    Get projects where user has 'admin' role in project_members.

    Returns:
        List of projects where user is admin, or empty list if none.
    """
    # Get project IDs where user is admin
    admin_r = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("project_id")
        .eq("user_id", user_id)
        .eq("role", "admin")
        .execute()
    )
    project_ids = [row["project_id"] for row in (admin_r.data or [])]

    if not project_ids:
        return []

    # Get project details for admin projects
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


def get_project_members(
    supabase: Client, project_id: str
) -> list[ProjectMemberResponse]:
    """
    Get all members of a specific project with their roles.
    Used for assignee dropdowns and member management UI.

    Returns:
        List of ProjectMemberResponse with user info
    """
    from app.modules.users.service import get_profiles_by_ids

    # Get project members
    r = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("user_id, role, created_at")
        .eq("project_id", project_id)
        .order("created_at", desc=False)
        .execute()
    )

    if not r.data:
        return []

    members_data = r.data
    user_ids = [m["user_id"] for m in members_data]

    # Get user profiles
    profiles = get_profiles_by_ids(supabase, user_ids)
    profile_map = {p.id: p for p in profiles}

    # Build response with user info
    result = []
    for m in members_data:
        profile = profile_map.get(m["user_id"])
        result.append(
            ProjectMemberResponse(
                project_id=project_id,
                user_id=m["user_id"],
                role=m["role"],
                created_at=m.get("created_at"),
                # Add user info for UI display
                user_email=profile.email if profile else None,
                user_full_name=profile.full_name if profile else None,
                user_avatar_url=profile.avatar_url if profile else None,
            )
        )
    return result


def check_user_in_project(
    supabase: Client, project_id: str, user_id: str
) -> bool:
    """
    Check if user is member of project (any role).
    Used for task assignment validation.
    """
    r = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("user_id")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return len(r.data or []) > 0


def is_project_admin(
    supabase: Client, project_id: str, user_id: str
) -> bool:
    """
    Check if user is admin of specific project.
    """
    r = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("role")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .eq("role", "admin")
        .limit(1)
        .execute()
    )
    return len(r.data or []) > 0


def count_project_admins(supabase: Client, project_id: str) -> int:
    """
    Count number of admins in project.
    Used to prevent removing last admin.
    """
    r = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("user_id", count="exact")
        .eq("project_id", project_id)
        .eq("role", "admin")
        .execute()
    )
    return r.count or 0


def list_project_members(supabase: Client, project_id: str) -> list[ProjectMemberResponse]:
    """Deprecated: Use get_project_members instead."""
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


def list_project_updates(supabase: Client, project_id: str, tenant_id: str) -> list[ProjectUpdateNoteResponse]:
    """List all update notes for a project with tenant isolation.

    Returns updates ordered by created_at DESC with author information populated.
    Only returns updates for projects that belong to the user's tenant.
    """
    # Query with join to verify tenant isolation
    # We join to projects table to ensure the project belongs to the user's tenant
    r = (
        supabase.schema(DB_SCHEMA)
        .table("project_updates")
        .select("*, projects!inner(tenant_id)")
        .eq("project_id", project_id)
        .eq("projects.tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )

    rows = r.data or []

    # Collect unique author IDs
    author_ids = list({row["author_id"] for row in rows if row.get("author_id")})

    # Fetch profiles for all authors
    author_profiles = {}
    if author_ids:
        profiles_r = (
            supabase.schema(DB_SCHEMA)
            .table("profiles")
            .select("id, email, full_name")
            .in_("id", author_ids)
            .execute()
        )
        for profile in (profiles_r.data or []):
            author_profiles[profile["id"]] = UserBasicInfo(
                id=profile["id"],
                email=profile.get("email", ""),
                full_name=profile.get("full_name"),
            )

    # Build response with author info
    updates = []
    for row in rows:
        author_id = row["author_id"]
        author = author_profiles.get(author_id, UserBasicInfo(
            id=author_id,
            email="",
            full_name=None,
        ))

        updates.append(
            ProjectUpdateNoteResponse(
                id=row["id"],
                project_id=row["project_id"],
                author_id=author_id,
                author=author,
                note=row["note"],
                created_at=row.get("created_at"),
            )
        )

    return updates


def add_project_update(
    supabase: Client, project_id: str, user_id: str, tenant_id: str, note: str
) -> ProjectUpdateNoteResponse:
    """Add a new update note to a project.

    Verifies user has access to project (tenant isolation check).
    Updates the project's last_activity_at timestamp.
    Returns the created update with author information.
    """
    # Validate note
    note = note.strip()
    if not note:
        raise ValueError("Note cannot be empty")

    # Verify user has access to project (tenant isolation)
    project = get_project(supabase, project_id, tenant_id)
    if not project:
        raise ValueError("Project not found or access denied")

    # Insert the update
    row = {
        "project_id": project_id,
        "author_id": user_id,
        "note": note,
    }

    r = supabase.schema(DB_SCHEMA).table("project_updates").insert(row).execute()

    data = (r.data or [None])[0]
    if not data:
        raise ValueError("Insert did not return row")

    # Update project's last_activity_at
    now = datetime.now(timezone.utc).isoformat()
    supabase.schema(DB_SCHEMA).table("projects").update(
        {"last_activity_at": now}
    ).eq("id", project_id).eq("tenant_id", tenant_id).execute()

    # Fetch author profile
    try:
        profile_r = (
            supabase.schema(DB_SCHEMA)
            .table("profiles")
            .select("id, email, full_name")
            .eq("id", user_id)
            .execute()
        )
        profile_data = (profile_r.data or [{}])[0] if profile_r.data else {}
    except Exception:
        # Profile not found, use defaults
        profile_data = {}

    author = UserBasicInfo(
        id=user_id,
        email=profile_data.get("email", ""),
        full_name=profile_data.get("full_name"),
    )

    return ProjectUpdateNoteResponse(
        id=data["id"],
        project_id=data["project_id"],
        author_id=data["author_id"],
        author=author,
        note=data["note"],
        created_at=data.get("created_at"),
    )
