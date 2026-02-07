from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import (
    get_current_user,
    get_supabase_client,
    get_tenant_id,
    require_tenant_org_admin,
)
from app.modules.master_materials.schemas import (
    MasterMaterialCreate,
    MasterMaterialResponse,
    MasterMaterialUpdate,
)
from app.modules.master_materials.service import (
    create_master_material,
    delete_master_material,
    get_master_material,
    list_master_materials,
    master_material_used_in_user_admin_projects,
    update_master_material,
)
from supabase import Client

router = APIRouter()


def _can_edit_master_material(
    master_material_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
) -> str:
    """Allow org_admin always; project_admin only if master is used in a project they admin."""
    from app.core.dependencies import get_tenant_membership

    role = get_tenant_membership(tenant_id, current_user["id"], supabase)
    if role == "org_admin":
        return master_material_id
    master = get_master_material(supabase, master_material_id, tenant_id)
    if not master:
        raise HTTPException(status_code=404, detail="Master material not found")
    if role == "member" or role is None:
        raise HTTPException(status_code=403, detail="Only org admin or project admin can edit this master material")
    if master_material_used_in_user_admin_projects(supabase, master_material_id, current_user["id"], tenant_id):
        return master_material_id
    raise HTTPException(status_code=403, detail="You can only edit master materials used in projects you admin")


@router.get("", response_model=list[MasterMaterialResponse])
def list_master_materials_route(
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    return list_master_materials(supabase, tenant_id)


@router.post("", response_model=MasterMaterialResponse, status_code=201)
def create_master_material_route(
    payload: MasterMaterialCreate,
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
):
    from app.core.constants import MATERIAL_UNITS

    if payload.unit not in MATERIAL_UNITS:
        raise HTTPException(status_code=400, detail=f"unit must be one of: {list(MATERIAL_UNITS)}")
    return create_master_material(supabase, tenant_id, payload)


@router.patch("/{master_material_id}", response_model=MasterMaterialResponse)
def update_master_material_route(
    master_material_id: str,
    payload: MasterMaterialUpdate,
    _: str = Depends(_can_edit_master_material),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    if payload.unit is not None:
        from app.core.constants import MATERIAL_UNITS

        if payload.unit not in MATERIAL_UNITS:
            raise HTTPException(status_code=400, detail=f"unit must be one of: {list(MATERIAL_UNITS)}")
    try:
        return update_master_material(supabase, master_material_id, tenant_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Master material not found")


@router.delete("/{master_material_id}", status_code=204)
def delete_master_material_route(
    master_material_id: str,
    _: str = Depends(_can_edit_master_material),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    try:
        delete_master_material(supabase, master_material_id, tenant_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Master material not found")
