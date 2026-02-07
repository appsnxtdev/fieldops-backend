from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_bearer_token, get_current_user, get_supabase_client, require_tenant_org_admin
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
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
) -> list[UserProfileResponse]:
    ids = [x.strip() for x in user_ids.split(",") if x.strip()]
    if not ids:
        return []
    members = list_members(supabase, tenant_id)
    allowed_ids = {m.user_id for m in members}
    filtered = [i for i in ids if i in allowed_ids]
    return get_profiles_by_ids(supabase, filtered)
