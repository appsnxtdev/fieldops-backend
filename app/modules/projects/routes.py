from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import DEMO_CACHE_TTL, CacheKeys, cache_delete, cache_get, cache_set, get_redis_client, is_demo_user
from app.core.constants import DB_SCHEMA
from app.core.dependencies import (
    get_current_user,
    get_project_access,
    get_supabase_client,
    get_tenant_id,
    get_tenant_membership,
    require_tenant_org_admin,
)
from app.core.permissions import CAN_MANAGE_MEMBERS, CAN_MANAGE_PROJECT, CAN_VIEW_PROJECT
from app.modules.projects.schemas import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectMyAccessResponse,
    ProjectResponse,
    ProjectStatusUpdateRequest,
    ProjectUpdate,
    ProjectUpdateNoteCreate,
    ProjectUpdateNoteResponse,
)
from app.modules.projects.service import (
    add_project_member,
    add_project_update,
    check_user_in_project,
    count_project_admins,
    create_project,
    delete_project,
    get_project,
    get_project_members,
    list_project_members,
    list_project_updates,
    list_projects,
    remove_project_member,
    update_project,
    update_project_member,
)
from supabase import Client

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
def list_my_projects(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    role = get_tenant_membership(tenant_id, current_user["id"], supabase, redis=redis)

    # Cache for org_admin and demo users (demo gets 7-day persistent cache)
    should_cache = role == "org_admin" or is_demo_user(role)

    if should_cache:
        if is_demo_user(role):
            key = CacheKeys.demo_projects(tenant_id)
            ttl = DEMO_CACHE_TTL
        else:
            key = CacheKeys.projects_admin(tenant_id)
            ttl = 120

        cached = cache_get(redis, key)
        if cached is not None:
            return cached

    result = list_projects(supabase, tenant_id, current_user["id"], tenant_role=role)

    if should_cache:
        cache_set(redis, key, [r.model_dump() for r in result], ttl=ttl)

    return result


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project_route(
    payload: ProjectCreate,
    tenant_id: str = Depends(require_tenant_org_admin),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    result = create_project(supabase, tenant_id, payload, current_user["id"])
    cache_delete(redis, CacheKeys.projects_admin(tenant_id))
    return result


@router.get("/my-admin-projects", response_model=list[str])
def list_my_admin_projects(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """List project IDs where current user is an admin."""
    r = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("project_id")
        .eq("user_id", current_user["id"])
        .eq("role", "admin")
        .execute()
    )

    project_ids = [row["project_id"] for row in (r.data or [])]

    # Verify projects belong to user's tenant
    if project_ids:
        projects_r = (
            supabase.schema(DB_SCHEMA)
            .table("projects")
            .select("id")
            .eq("tenant_id", tenant_id)
            .in_("id", project_ids)
            .execute()
        )
        verified_ids = [row["id"] for row in (projects_r.data or [])]
        return verified_ids

    return []


@router.get("/{project_id}/my-access", response_model=ProjectMyAccessResponse)
def get_my_project_access(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
):
    return ProjectMyAccessResponse(role=access["role"])


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    proj = get_project(supabase, project_id, access["tenant_id"])
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project_route(
    project_id: str,
    payload: ProjectUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    result = update_project(supabase, project_id, access["tenant_id"], payload)
    cache_delete(redis, CacheKeys.projects_admin(access["tenant_id"]))
    return result


@router.put("/{project_id}", response_model=ProjectResponse)
def put_project_route(
    project_id: str,
    payload: ProjectUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    result = update_project(supabase, project_id, access["tenant_id"], payload, full_replace=True)
    cache_delete(redis, CacheKeys.projects_admin(access["tenant_id"]))
    return result


@router.delete("/{project_id}", status_code=204)
def delete_project_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    delete_project(supabase, project_id, access["tenant_id"])
    cache_delete(redis, CacheKeys.projects_admin(access["tenant_id"]))


@router.get("/{project_id}/updates", response_model=list[ProjectUpdateNoteResponse])
def list_project_updates_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    """List all update notes for a project."""
    return list_project_updates(supabase, project_id, access["tenant_id"])


@router.post("/{project_id}/updates", response_model=ProjectUpdateNoteResponse, status_code=201)
def add_project_update_route(
    project_id: str,
    payload: ProjectUpdateNoteCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_PROJECT)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Add a new update note to a project."""
    try:
        return add_project_update(
            supabase,
            project_id,
            current_user["id"],
            access["tenant_id"],
            payload.note,
        )
    except ValueError as e:
        # Convert ValueError from service to appropriate HTTP error
        error_msg = str(e)
        if "not found" in error_msg.lower() or "access denied" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)


@router.patch("/{project_id}/status", response_model=ProjectResponse)
def update_project_status_route(
    project_id: str,
    payload: ProjectStatusUpdateRequest,
    access: dict = Depends(get_project_access(CAN_MANAGE_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    """Update project status and last_activity_at timestamp."""
    try:
        # Update status and last_activity_at in a single database operation
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "status": payload.status,
            "last_activity_at": now,
        }

        supabase.schema(DB_SCHEMA).table("projects").update(data).eq(
            "id", project_id
        ).eq("tenant_id", access["tenant_id"]).execute()

        # Clear cache
        cache_delete(redis, CacheKeys.projects_admin(access["tenant_id"]))

        # Fetch the updated project
        updated_proj = get_project(supabase, project_id, access["tenant_id"])
        if not updated_proj:
            raise HTTPException(status_code=404, detail="Project not found")

        return updated_proj
    except ValueError as e:
        # Convert ValueError from service to appropriate HTTP error
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def list_members_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    """List all members of a project with user info."""
    return get_project_members(supabase, project_id)


@router.get("/{project_id}/members/me", response_model=ProjectMyAccessResponse)
def get_my_member_role(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
):
    """Get current user's role in the project."""
    return ProjectMyAccessResponse(role=access["role"])


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=201)
def add_member_route(
    project_id: str,
    payload: ProjectMemberCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    """Add a new member to the project.

    Only org_admin can set role='admin'.
    User must be a tenant member before being added to project.
    """
    # Only org_admin can create project admins (privilege escalation prevention)
    if payload.role == "admin" and access.get("tenant_role") != "org_admin":
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can assign project admin role"
        )

    # Validate user is a tenant member first
    from app.core.dependencies import get_tenant_membership
    from app.core.cache import get_redis_client
    redis = get_redis_client()
    user_tenant_role = get_tenant_membership(tenant_id, payload.user_id, supabase, redis=redis)
    if not user_tenant_role:
        raise HTTPException(
            status_code=400,
            detail="User must be a tenant member before being added to project"
        )

    result = add_project_member(supabase, project_id, payload)

    # Populate user info for response
    from app.modules.users.service import get_profiles_by_ids
    profiles = get_profiles_by_ids(supabase, [payload.user_id])
    if profiles:
        profile = profiles[0]
        result.user_email = profile.email
        result.user_full_name = profile.full_name
        result.user_avatar_url = profile.avatar_url

    return result


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def update_member_route(
    project_id: str,
    user_id: str,
    payload: ProjectMemberUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    """Update a project member's role.

    Only org_admin can promote to admin.
    Cannot demote the last admin.
    """
    # Only org_admin can promote to admin (privilege escalation prevention)
    if payload.role == "admin" and access.get("tenant_role") != "org_admin":
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can assign project admin role"
        )

    # Cannot demote last admin
    if payload.role != "admin":
        admin_count = count_project_admins(supabase, project_id)
        # Check if target user is currently an admin
        current_member = (
            supabase.schema(DB_SCHEMA)
            .table("project_members")
            .select("role")
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if current_member.data and current_member.data[0].get("role") == "admin":
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot demote the last project admin"
                )

    result = update_project_member(supabase, project_id, user_id, payload.role)

    # Populate user info for response
    from app.modules.users.service import get_profiles_by_ids
    profiles = get_profiles_by_ids(supabase, [user_id])
    if profiles:
        profile = profiles[0]
        result.user_email = profile.email
        result.user_full_name = profile.full_name
        result.user_avatar_url = profile.avatar_url

    return result


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member_route(
    project_id: str,
    user_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    """Remove a member from the project.

    Cannot remove the last admin.
    """
    # Cannot remove last admin
    admin_count = count_project_admins(supabase, project_id)
    # Check if target user is an admin
    current_member = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("role")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if current_member.data and current_member.data[0].get("role") == "admin":
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last project admin"
            )

    remove_project_member(supabase, project_id, user_id)
