from fastapi import APIRouter, Depends, Query

from app.core.cache import get_redis_client
from app.core.constants import DB_SCHEMA
from app.core.dependencies import get_bearer_token, get_current_user, get_supabase_client, get_tenant_id, get_tenant_membership, require_tenant_org_admin
from app.core.tenants_client import get_core_user_me
from app.modules.users.schemas import UserProfileResponse
from app.modules.users.service import ensure_profile, get_me, get_profiles_by_ids
from app.modules.tenant_members.service import list_members
from supabase import Client

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
def me(
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_user),
    token: str = Depends(get_bearer_token),
) -> UserProfileResponse:
    core_user = get_core_user_me(token)
    ensure_profile(supabase, current_user, core_user=core_user)
    profile = get_me(supabase, current_user["id"])
    if not profile:
        return UserProfileResponse(id=current_user["id"], email=current_user.get("email"))
    return profile


@router.get("/profiles", response_model=list[UserProfileResponse])
def list_profiles(
    user_ids: str = Query(..., description="Comma-separated user UUIDs"),
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
) -> list[UserProfileResponse]:
    """
    Fetch user profiles filtered by role:
    - org_admin/demo: can fetch any tenant member profiles
    - project admin: can only fetch profiles of members in their projects
    - regular member: can only fetch profiles of members in projects they're assigned to
    """
    ids = [x.strip() for x in user_ids.split(",") if x.strip()]
    if not ids:
        return []

    # Get user's role
    role = get_tenant_membership(tenant_id, current_user["id"], supabase, redis=redis)

    # Get all tenant members
    members = list_members(supabase, tenant_id)
    allowed_ids = {m.user_id for m in members}

    # org_admin and demo users can see all tenant members
    if role in ("org_admin", "demo"):
        filtered = [i for i in ids if i in allowed_ids]
        return get_profiles_by_ids(supabase, filtered)

    # For project admins and members, filter to users in their projects
    # Get all projects where current user is a member (any role)
    user_projects = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("project_id")
        .eq("user_id", current_user["id"])
        .execute()
    )
    user_project_ids = [row["project_id"] for row in (user_projects.data or [])]

    if not user_project_ids:
        # User is not in any projects, return empty
        return []

    # Get all users in those projects
    project_members = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("user_id")
        .in_("project_id", user_project_ids)
        .execute()
    )
    project_user_ids = {row["user_id"] for row in (project_members.data or [])}

    # Filter requested IDs to only include users in same projects
    filtered = [i for i in ids if i in allowed_ids and i in project_user_ids]
    return get_profiles_by_ids(supabase, filtered)
