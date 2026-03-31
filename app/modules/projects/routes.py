from fastapi import APIRouter, Depends, HTTPException

from app.core.cache import DEMO_CACHE_TTL, CacheKeys, cache_delete, cache_get, cache_set, get_redis_client, is_demo_user
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
    ProjectUpdate,
)
from app.modules.projects.service import (
    add_project_member,
    create_project,
    delete_project,
    get_project,
    list_project_members,
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


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def list_members_route(
    project_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    from app.core.dependencies import get_tenant_membership

    # Check if user is org_admin - if so, allow viewing members of any project in tenant
    tenant_role = get_tenant_membership(tenant_id, current_user["id"], supabase, redis=redis)

    if tenant_role == "org_admin":
        # Org admins can view members of any project in their tenant
        # Just verify the project belongs to their tenant
        proj = get_project(supabase, project_id, tenant_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        return list_project_members(supabase, project_id)
    else:
        # Non-org_admins need CAN_MANAGE_MEMBERS permission on the project
        # This will be checked by requiring the user to be a project member with appropriate role
        from app.core.dependencies import ensure_project_access
        from app.core.config import get_settings

        settings = get_settings()
        # We need the bearer token for ensure_project_access
        from fastapi import Request
        # Since we can't inject Request here easily, let's use a simpler check
        # Check project membership directly
        from app.core.constants import DB_SCHEMA
        mem_result = (
            supabase.schema(DB_SCHEMA).table("project_members")
            .select("role")
            .eq("project_id", project_id)
            .eq("user_id", current_user["id"])
            .limit(1)
            .execute()
        )
        mem = mem_result.data[0] if mem_result.data else None
        if not mem:
            raise HTTPException(status_code=403, detail="Not a project member")

        from app.core.permissions import has_permission
        role = mem.get("role") or "viewer"
        if not has_permission(role, CAN_MANAGE_MEMBERS):
            raise HTTPException(status_code=403, detail="Insufficient permission")

        return list_project_members(supabase, project_id)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=201)
def add_member_route(
    project_id: str,
    payload: ProjectMemberCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    return add_project_member(supabase, project_id, payload)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def update_member_route(
    project_id: str,
    user_id: str,
    payload: ProjectMemberUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    return update_project_member(supabase, project_id, user_id, payload.role)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member_route(
    project_id: str,
    user_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    remove_project_member(supabase, project_id, user_id)
