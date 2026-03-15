from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_supabase_client, get_tenant_id, require_tenant_org_admin
from app.modules.labour.schemas import LabourTypeCreate, LabourTypeResponse, LabourTypeUpdate
from app.modules.labour.service import (
    create_labour_type,
    delete_labour_type,
    get_labour_type,
    list_labour_types,
    update_labour_type,
)
from supabase import Client

router = APIRouter()


@router.get("", response_model=list[LabourTypeResponse])
def list_types(
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    return list_labour_types(supabase, tenant_id)


@router.post("", response_model=LabourTypeResponse, status_code=201)
def create_type(
    payload: LabourTypeCreate,
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
):
    return create_labour_type(supabase, tenant_id, payload)


@router.patch("/{type_id}", response_model=LabourTypeResponse)
def update_type(
    type_id: str,
    payload: LabourTypeUpdate,
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
):
    try:
        return update_labour_type(supabase, type_id, tenant_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Labour type not found")


@router.delete("/{type_id}", status_code=204)
def delete_type(
    type_id: str,
    tenant_id: str = Depends(require_tenant_org_admin),
    supabase: Client = Depends(get_supabase_client),
):
    try:
        delete_labour_type(supabase, type_id, tenant_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Labour type not found")
