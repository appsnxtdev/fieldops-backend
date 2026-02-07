from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.master_materials.schemas import (
    MasterMaterialCreate,
    MasterMaterialResponse,
    MasterMaterialUpdate,
)


def list_master_materials(supabase: Client, tenant_id: str) -> list[MasterMaterialResponse]:
    r = (
        supabase.schema(DB_SCHEMA)
        .table("master_materials")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at")
        .execute()
    )
    return [MasterMaterialResponse(**row) for row in (r.data or [])]


def get_master_material(supabase: Client, master_material_id: str, tenant_id: str) -> MasterMaterialResponse | None:
    r = (
        supabase.schema(DB_SCHEMA)
        .table("master_materials")
        .select("*")
        .eq("id", master_material_id)
        .eq("tenant_id", tenant_id)
        .maybe_single()
        .execute()
    )
    return MasterMaterialResponse(**r.data) if r.data else None


def create_master_material(supabase: Client, tenant_id: str, payload: MasterMaterialCreate) -> MasterMaterialResponse:
    row = {"tenant_id": tenant_id, "name": payload.name, "unit": payload.unit}
    r = supabase.schema(DB_SCHEMA).table("master_materials").insert(row).execute()
    row_out = (r.data or [None])[0]
    if not row_out:
        raise ValueError("Insert failed")
    return MasterMaterialResponse(**row_out)


def update_master_material(
    supabase: Client, master_material_id: str, tenant_id: str, payload: MasterMaterialUpdate
) -> MasterMaterialResponse:
    data = payload.model_dump(exclude_unset=True)
    r = (
        supabase.schema(DB_SCHEMA)
        .table("master_materials")
        .update(data)
        .eq("id", master_material_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    row = (r.data or [None])[0]
    if not row:
        raise ValueError("Master material not found")
    return MasterMaterialResponse(**row)


def delete_master_material(supabase: Client, master_material_id: str, tenant_id: str) -> None:
    supabase.schema(DB_SCHEMA).table("master_materials").delete().eq("id", master_material_id).eq("tenant_id", tenant_id).execute()


def master_material_used_in_user_admin_projects(
    supabase: Client, master_material_id: str, user_id: str, tenant_id: str
) -> bool:
    """True if any project material links to this master and user is admin of that project."""
    admin_projects = (
        supabase.schema(DB_SCHEMA)
        .table("project_members")
        .select("project_id")
        .eq("user_id", user_id)
        .eq("role", "admin")
        .execute()
    )
    project_ids = [r["project_id"] for r in (admin_projects.data or [])]
    if not project_ids:
        return False
    used = (
        supabase.schema(DB_SCHEMA)
        .table("materials")
        .select("id")
        .eq("master_material_id", master_material_id)
        .in_("project_id", project_ids)
        .limit(1)
        .execute()
    )
    return bool(used.data)
