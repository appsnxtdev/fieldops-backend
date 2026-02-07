import uuid
from decimal import Decimal
from fastapi import UploadFile
from supabase import Client

from app.core.constants import DB_SCHEMA, MATERIAL_UNITS
from app.modules.materials.schemas import (
    LedgerEntryResponse,
    MaterialCreate,
    MaterialResponse,
    MaterialWithBalanceResponse,
    MaterialUpdate,
)


def get_material(supabase: Client, material_id: str, project_id: str) -> MaterialResponse | None:
    r = supabase.schema(DB_SCHEMA).table("materials").select("*").eq("id", material_id).eq("project_id", project_id).maybe_single().execute()
    return MaterialResponse(**r.data) if r.data else None


def list_materials(supabase: Client, project_id: str) -> list[MaterialResponse]:
    r = supabase.schema(DB_SCHEMA).table("materials").select("*").eq("project_id", project_id).order("created_at").execute()
    return [MaterialResponse(**row) for row in (r.data or [])]


def get_material_balance(supabase: Client, material_id: str) -> float:
    r = supabase.schema(DB_SCHEMA).table("material_ledger").select("type, quantity").eq("material_id", material_id).execute()
    total = Decimal("0")
    for row in r.data or []:
        if row["type"] == "in":
            total += Decimal(str(row["quantity"]))
        else:
            total -= Decimal(str(row["quantity"]))
    return float(total)


def list_materials_with_balance(supabase: Client, project_id: str) -> list[MaterialWithBalanceResponse]:
    materials = list_materials(supabase, project_id)
    out = []
    for m in materials:
        balance = get_material_balance(supabase, m.id)
        out.append(MaterialWithBalanceResponse(**(m.model_dump()), balance=balance))
    return out


def create_material(
    supabase: Client, project_id: str, payload: MaterialCreate, tenant_id: str
) -> MaterialResponse:
    if payload.master_material_id:
        from app.modules.master_materials.service import get_master_material

        master = get_master_material(supabase, payload.master_material_id, tenant_id)
        if not master:
            raise ValueError("Master material not found")
        name, unit, mid = master.name, master.unit, payload.master_material_id
    else:
        if not payload.name or not payload.unit:
            raise ValueError("name and unit required when master_material_id not set")
        if payload.unit not in MATERIAL_UNITS:
            raise ValueError(f"unit must be one of: {list(MATERIAL_UNITS)}")
        name, unit, mid = payload.name, payload.unit, None
    row = {"project_id": project_id, "name": name, "unit": unit, "master_material_id": mid}
    r = supabase.schema(DB_SCHEMA).table("materials").insert(row).execute()
    row_out = (r.data or [None])[0]
    if not row_out:
        raise ValueError("Insert failed")
    return MaterialResponse(**row_out)


def update_material(supabase: Client, material_id: str, project_id: str, payload: MaterialUpdate) -> MaterialResponse:
    data = payload.model_dump(exclude_unset=True)
    if "unit" in data and data["unit"] not in MATERIAL_UNITS:
        raise ValueError(f"unit must be one of: {list(MATERIAL_UNITS)}")
    r = supabase.schema(DB_SCHEMA).table("materials").update(data).eq("id", material_id).eq("project_id", project_id).execute()
    row = (r.data or [None])[0]
    if not row:
        raise ValueError("Material not found")
    return MaterialResponse(**row)


def delete_material(supabase: Client, material_id: str, project_id: str) -> None:
    supabase.schema(DB_SCHEMA).table("materials").delete().eq("id", material_id).eq("project_id", project_id).execute()


RECEIPT_BUCKET = "material_receipts"


def upload_ledger_receipt(supabase: Client, project_id: str, material_id: str, file: UploadFile) -> str:
    ext = (file.filename or "").split(".")[-1] if file.filename else "bin"
    if ext.lower() not in ("pdf", "jpg", "jpeg", "png", "heic", "webp"):
        ext = "bin"
    path = f"{project_id}/{material_id}/{uuid.uuid4().hex}.{ext}"
    content = file.file.read()
    supabase.storage.from_(RECEIPT_BUCKET).upload(
        path, content, file_options={"content-type": file.content_type or "application/octet-stream"}
    )
    return path


def add_ledger_entry(
    supabase: Client,
    material_id: str,
    type_: str,
    quantity: float,
    notes: str | None,
    created_by: str,
    receipt_path: str | None = None,
) -> LedgerEntryResponse:
    row = {
        "material_id": material_id,
        "type": type_,
        "quantity": quantity,
        "notes": notes,
        "created_by": created_by,
    }
    if receipt_path is not None:
        row["receipt_path"] = receipt_path
    r = supabase.schema(DB_SCHEMA).table("material_ledger").insert(row).execute()
    row_out = (r.data or [None])[0]
    if not row_out:
        raise ValueError("Insert failed")
    return LedgerEntryResponse(**row_out)


def list_ledger(supabase: Client, material_id: str) -> list[LedgerEntryResponse]:
    r = supabase.schema(DB_SCHEMA).table("material_ledger").select("*").eq("material_id", material_id).order("created_at").execute()
    return [LedgerEntryResponse(**row) for row in (r.data or [])]
