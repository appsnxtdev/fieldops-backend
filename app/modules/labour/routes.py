import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_current_user, get_project_access_query, get_supabase_client, get_tenant_id
from app.core.constants import DB_SCHEMA
from app.core.permissions import CAN_MANAGE_EXPENSE, CAN_VIEW_ATTENDANCE
from app.modules.labour.schemas import LabourDailyCreateBody
from supabase import Client

router = APIRouter()


@router.get("/daily")
def get_labour_daily(
    date: str = Query(..., description="YYYY-MM-DD"),
    access: dict = Depends(get_project_access_query(CAN_VIEW_ATTENDANCE)),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    from app.modules.labour.service import list_labour_daily_for_date

    return list_labour_daily_for_date(supabase, access["project_id"], date, tenant_id)


@router.post("/daily")
def post_labour_daily(
    payload: LabourDailyCreateBody,
    access: dict = Depends(get_project_access_query(CAN_MANAGE_EXPENSE)),
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    from app.modules.labour.service import upsert_labour_daily

    project_id = access["project_id"]
    return upsert_labour_daily(
        supabase,
        project_id,
        payload.date,
        [e.model_dump() for e in payload.entries],
        current_user["id"],
        tenant_id,
    )


@router.get("/export")
def export_labour(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    access: dict = Depends(get_project_access_query(CAN_VIEW_ATTENDANCE)),
    supabase: Client = Depends(get_supabase_client),
):
    project_id = access["project_id"]
    rows = list_labour_in_range(supabase, project_id, from_date, to_date)
    type_ids = list({r["labour_type_id"] for r in rows})
    types_r = (
        supabase.schema(DB_SCHEMA)
        .table("labour_types")
        .select("id, name, rate_per_day")
        .in_("id", type_ids)
        .execute()
    )
    type_map = {x["id"]: x for x in (types_r.data or [])}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "labour_type", "rate_per_day", "count", "amount"])
    for r in rows:
        t = type_map.get(r["labour_type_id"], {})
        name = t.get("name", "")
        rate = float(t.get("rate_per_day", 0))
        count = int(r.get("count", 0))
        amount = round(count * rate, 2)
        w.writerow([r.get("date"), name, rate, count, amount])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=labour_{project_id}_{from_date}_{to_date}.csv"},
    )
