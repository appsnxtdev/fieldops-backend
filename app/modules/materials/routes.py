from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.core.cache import DEMO_CACHE_TTL, CacheKeys, cache_delete, cache_get, cache_set, get_redis_client, is_demo_user
from app.core.constants import DB_SCHEMA
from app.core.dependencies import (
    _first_row,
    get_current_user,
    get_project_access,
    get_supabase_client,
    get_tenant_id,
)
from app.core.permissions import CAN_MANAGE_MATERIALS, CAN_VIEW_MATERIALS
from app.modules.materials.schemas import (
    LedgerEntryResponse,
    MaterialCreate,
    MaterialResponse,
    MaterialUpdate,
    MaterialWithBalanceResponse,
    ProjectMaterialsSummary,
)
from app.modules.materials.service import (
    add_ledger_entry,
    create_material,
    delete_material,
    get_material,
    list_ledger,
    list_materials_with_balance,
    update_material,
    upload_ledger_receipt,
)
from supabase import Client

router = APIRouter()


def _project_ids_user_can_view(
    supabase: Client, tenant_id: str, user_id: str, requested_ids: list[str],
) -> list[tuple[str, str]]:
    """Return (project_id, project_name) for each requested project user can view."""
    tenant_role_r = (
        supabase.schema(DB_SCHEMA).table("tenant_members").select("role").eq("tenant_id", tenant_id).eq("user_id", user_id).maybe_single().execute()
    )
    tenant_role = _first_row(tenant_role_r)
    role = (tenant_role.get("role") if tenant_role else None) or "member"
    return _project_ids_user_can_view_with_role(supabase, tenant_id, user_id, requested_ids, role)


def _project_ids_user_can_view_with_role(
    supabase: Client, tenant_id: str, user_id: str, requested_ids: list[str], role: str | None
) -> list[tuple[str, str]]:
    """Return (project_id, project_name) for each requested project user can view, given a known role."""
    role = role or "member"
    # org_admin and demo users can view all projects
    if role in ("org_admin", "demo"):
        r = supabase.schema(DB_SCHEMA).table("projects").select("id, name").eq("tenant_id", tenant_id).in_("id", requested_ids or []).execute()
        return [(row["id"], row["name"]) for row in (r.data or [])]
    r = (
        supabase.schema(DB_SCHEMA).table("project_members").select("project_id").eq("user_id", user_id).execute()
    )
    allowed_ids = {row["project_id"] for row in (r.data or [])}
    allowed_ids &= set(requested_ids)
    if not allowed_ids:
        return []
    projs = supabase.schema(DB_SCHEMA).table("projects").select("id, name").in_("id", list(allowed_ids)).execute()
    return [(row["id"], row["name"]) for row in (projs.data or [])]


@router.get("/summary", response_model=list[ProjectMaterialsSummary])
def materials_summary_route(
    project_ids: str = Query(..., description="Comma-separated project IDs"),
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    ids = [x.strip() for x in project_ids.split(",") if x.strip()]
    if not ids:
        return []

    # Get tenant role using cached function
    from app.core.dependencies import get_tenant_membership
    tenant_role = get_tenant_membership(tenant_id, current_user["id"], supabase, redis=redis)
    is_demo = is_demo_user(tenant_role)

    if is_demo:
        key = CacheKeys.demo_materials_summary(project_ids)
        ttl = DEMO_CACHE_TTL
    else:
        # Regular users don't get cached summary (varies per user permissions)
        key = None
        ttl = 0

    if key:
        cached = cache_get(redis, key)
        if cached is not None:
            # If cache is empty but we have project IDs, it's stale - invalidate it
            if len(cached) == 0 and len(ids) > 0:
                cache_delete(redis, key)
            else:
                return [ProjectMaterialsSummary(**item) for item in cached]

    # Use the already-fetched tenant_role to avoid redundant DB query
    projects = _project_ids_user_can_view_with_role(supabase, tenant_id, current_user["id"], ids, tenant_role)
    out = []
    for pid, pname in projects:
        materials = list_materials_with_balance(supabase, pid)
        out.append(ProjectMaterialsSummary(project_id=pid, project_name=pname, materials=materials))

    if key:
        cache_set(redis, key, [item.model_dump() for item in out], ttl=ttl)

    return out


@router.get("/{project_id}/materials", response_model=list[MaterialWithBalanceResponse])
def list_materials_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_MATERIALS)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    # Check if demo user for persistent caching
    tenant_role = access.get("tenant_role")
    is_demo = is_demo_user(tenant_role)

    if is_demo:
        key = CacheKeys.demo_materials(project_id)
        ttl = DEMO_CACHE_TTL
    else:
        key = CacheKeys.materials(project_id)
        ttl = 120

    cached = cache_get(redis, key)
    if cached is not None:
        return [MaterialWithBalanceResponse(**item) for item in cached]

    result = list_materials_with_balance(supabase, project_id)
    cache_set(redis, key, [item.model_dump() for item in result], ttl=ttl)
    return result


@router.post("/{project_id}/materials", response_model=MaterialResponse, status_code=201)
def create_material_route(
    project_id: str,
    payload: MaterialCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_MATERIALS)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    if not payload.master_material_id and (not payload.name or not payload.unit):
        raise HTTPException(status_code=400, detail="Provide master_material_id or both name and unit")
    try:
        result = create_material(supabase, project_id, payload, access["tenant_id"])
        cache_delete(redis, CacheKeys.materials(project_id))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{project_id}/materials/{material_id}", response_model=MaterialResponse)
def update_material_route(
    project_id: str,
    material_id: str,
    payload: MaterialUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_MATERIALS)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    try:
        result = update_material(supabase, material_id, project_id, payload)
        cache_delete(redis, CacheKeys.materials(project_id))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}/materials/{material_id}", status_code=204)
def delete_material_route(
    project_id: str,
    material_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_MATERIALS)),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    delete_material(supabase, material_id, project_id)
    cache_delete(redis, CacheKeys.materials(project_id))


@router.get("/{project_id}/materials/{material_id}/ledger", response_model=list[LedgerEntryResponse])
def list_ledger_route(
    project_id: str,
    material_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_MATERIALS)),
    supabase: Client = Depends(get_supabase_client),
):
    if not get_material(supabase, material_id, project_id):
        raise HTTPException(status_code=404, detail="Material not found")
    return list_ledger(supabase, material_id)


@router.post("/{project_id}/materials/{material_id}/ledger", response_model=LedgerEntryResponse, status_code=201)
def add_ledger_entry_route(
    project_id: str,
    material_id: str,
    type_: str = Form(..., alias="type"),
    quantity: float = Form(...),
    notes: str | None = Form(None),
    receipt: UploadFile | None = File(None),
    access: dict = Depends(get_project_access(CAN_MANAGE_MATERIALS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    if type_ not in ("in", "out"):
        raise HTTPException(status_code=400, detail="type must be 'in' or 'out'")
    if not get_material(supabase, material_id, project_id):
        raise HTTPException(status_code=404, detail="Material not found")
    receipt_path = None
    if receipt and receipt.filename and type_ == "in":
        receipt_path = upload_ledger_receipt(supabase, project_id, material_id, receipt)
    result = add_ledger_entry(
        supabase, material_id, type_, quantity, notes, current_user["id"], receipt_path=receipt_path
    )
    cache_delete(redis, CacheKeys.materials(project_id))
    return result
