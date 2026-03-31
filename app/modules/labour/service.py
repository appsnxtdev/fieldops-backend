from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.labour.schemas import (
    LabourDailyEntryResponse,
    LabourTypeCreate,
    LabourTypeResponse,
    LabourTypeUpdate,
)


def list_labour_types(supabase: Client, tenant_id: str) -> list[LabourTypeResponse]:
    r = (
        supabase.schema(DB_SCHEMA)
        .table("labour_types")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("name")
        .execute()
    )
    return [LabourTypeResponse(**row) for row in (r.data or [])]


def create_labour_type(supabase: Client, tenant_id: str, payload: LabourTypeCreate) -> LabourTypeResponse:
    row = {
        "tenant_id": tenant_id,
        "name": payload.name.strip(),
        "rate_per_day": payload.rate_per_day,
    }
    r = supabase.schema(DB_SCHEMA).table("labour_types").insert(row).execute()
    data = (r.data or [None])[0]
    if not data:
        raise ValueError("Insert did not return row")
    return LabourTypeResponse(**data)


def get_labour_type(supabase: Client, type_id: str, tenant_id: str) -> LabourTypeResponse | None:
    r = (
        supabase.schema(DB_SCHEMA)
        .table("labour_types")
        .select("*")
        .eq("id", type_id)
        .eq("tenant_id", tenant_id)
        .maybe_single()
        .execute()
    )
    if not r.data:
        return None
    return LabourTypeResponse(**r.data)


def update_labour_type(
    supabase: Client, type_id: str, tenant_id: str, payload: LabourTypeUpdate
) -> LabourTypeResponse:
    t = get_labour_type(supabase, type_id, tenant_id)
    if not t:
        raise ValueError("Labour type not found")
    updates = {}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.rate_per_day is not None:
        updates["rate_per_day"] = payload.rate_per_day
    if not updates:
        return t
    r = (
        supabase.schema(DB_SCHEMA)
        .table("labour_types")
        .update(updates)
        .eq("id", type_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    data = (r.data or [None])[0]
    if not data:
        raise ValueError("Update did not return row")
    return LabourTypeResponse(**data)


def delete_labour_type(supabase: Client, type_id: str, tenant_id: str) -> None:
    t = get_labour_type(supabase, type_id, tenant_id)
    if not t:
        raise ValueError("Labour type not found")
    supabase.schema(DB_SCHEMA).table("labour_types").delete().eq("id", type_id).eq("tenant_id", tenant_id).execute()


def list_labour_daily_for_date(
    supabase: Client, project_id: str, date: str, tenant_id: str
) -> list[LabourDailyEntryResponse]:
    # Use a join to fetch labour_daily with labour_types in one query
    r = (
        supabase.schema(DB_SCHEMA)
        .table("labour_daily")
        .select("labour_type_id, count, labour_types!inner(id, name, rate_per_day, tenant_id)")
        .eq("project_id", project_id)
        .eq("date", date)
        .eq("labour_types.tenant_id", tenant_id)
        .execute()
    )
    rows = r.data or []
    result = []
    for row in rows:
        tid = row["labour_type_id"]
        type_data = row.get("labour_types", {})
        count = row.get("count", 0)
        rate = float(type_data.get("rate_per_day", 0))
        result.append(
            LabourDailyEntryResponse(
                labour_type_id=tid,
                labour_type_name=type_data.get("name", ""),
                rate_per_day=rate,
                count=count,
                amount=round(count * rate, 2),
            )
        )
    return sorted(result, key=lambda x: x.labour_type_name)


def upsert_labour_daily(
    supabase: Client,
    project_id: str,
    date: str,
    entries: list[dict],
    created_by: str,
    tenant_id: str,
) -> list[LabourDailyEntryResponse]:
    # Replace all entries for this project+date: delete then insert
    supabase.schema(DB_SCHEMA).table("labour_daily").delete().eq(
        "project_id", project_id
    ).eq("date", date).execute()
    for e in entries:
        type_id = e.get("labour_type_id")
        count = int(e.get("count", 0))
        if not type_id or count < 0:
            continue
        get_labour_type(supabase, type_id, tenant_id)  # validate type exists
        supabase.schema(DB_SCHEMA).table("labour_daily").insert(
            {
                "project_id": project_id,
                "date": date,
                "labour_type_id": type_id,
                "count": count,
                "created_by": created_by,
            },
        ).execute()
    return list_labour_daily_for_date(supabase, project_id, date, tenant_id)


def list_labour_in_range(
    supabase: Client, project_id: str, from_date: str, to_date: str
) -> list[dict]:
    r = (
        supabase.schema(DB_SCHEMA)
        .table("labour_daily")
        .select("*, labour_types(name, rate_per_day)")
        .eq("project_id", project_id)
        .gte("date", from_date)
        .lte("date", to_date)
        .order("date")
        .execute()
    )
    return list(r.data or [])
