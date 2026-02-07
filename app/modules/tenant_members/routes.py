from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_supabase_client, get_tenant_id, require_tenant_org_admin
from app.modules.tenant_members.schemas import TenantMemberCreate, TenantMemberResponse, TenantMemberUpdate
from app.modules.tenant_members.service import add_member, list_members, remove_member, update_member
from postgrest.exceptions import APIError
from supabase import Client

router = APIRouter()


@router.get("", response_model=list[TenantMemberResponse])
def list_tenant_members(
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
):
    return list_members(supabase, tenant_id)


@router.post("", response_model=TenantMemberResponse, status_code=201)
def create_tenant_member(
    payload: TenantMemberCreate,
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
):
    try:
        return add_member(supabase, tenant_id, payload)
    except ValueError as e:
        if str(e) == "user_not_found":
            raise HTTPException(
                status_code=404,
                detail="User not found. No auth user with this email. They must sign in at least once before being added.",
            )
        raise
    except APIError as e:
        if e.code == "23503":
            raise HTTPException(
                status_code=404,
                detail="User not found. The user must sign in to this app at least once before they can be added.",
            )
        raise


@router.patch("/{user_id}", response_model=TenantMemberResponse)
def patch_tenant_member(
    user_id: str,
    payload: TenantMemberUpdate,
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
):
    try:
        return update_member(supabase, tenant_id, user_id, payload.role)
    except ValueError as e:
        if str(e) == "tenant_member_not_found":
            raise HTTPException(status_code=404, detail="Tenant member not found")
        raise


@router.delete("/{user_id}", status_code=204)
def delete_tenant_member(
    user_id: str,
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
):
    remove_member(supabase, tenant_id, user_id)
