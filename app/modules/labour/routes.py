import csv
import io
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.cache import DEMO_CACHE_TTL, CacheKeys, cache_get, cache_set, get_redis_client, is_demo_user
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
    from app.modules.labour.schemas import LabourDailyResponse

    entries = list_labour_daily_for_date(supabase, access["project_id"], date, tenant_id)
    return LabourDailyResponse(
        project_id=access["project_id"],
        date=date,
        entries=entries,
    )


@router.get("/bulk")
def get_labour_bulk(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    access: dict = Depends(get_project_access_query(CAN_VIEW_ATTENDANCE)),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    """Get labour daily entries for a project across a date range (bulk fetch to reduce API calls)."""
    # Validate date format
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, from_date) or not re.match(date_pattern, to_date):
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

    from app.modules.labour.service import list_labour_in_range

    project_id = access["project_id"]

    # Check if demo user for persistent caching (7-day TTL vs 2-min TTL)
    tenant_role = access.get("tenant_role")
    is_demo = is_demo_user(tenant_role)

    if is_demo:
        key = CacheKeys.demo_labour_bulk(project_id, from_date, to_date)
        ttl = DEMO_CACHE_TTL
    else:
        key = CacheKeys.labour_bulk(project_id, from_date, to_date)
        ttl = 120

    cached = cache_get(redis, key)
    if cached is not None:
        return cached

    try:
        rows = list_labour_in_range(supabase, project_id, from_date, to_date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date range: {str(e)}")
    if not rows:
        result = {"by_date": {}}
        cache_set(redis, key, result, ttl=ttl)
        return result

    # Group by date
    by_date: dict[str, list[dict]] = {}
    for row in rows:
        date = row.get("date")
        if not date:
            continue

        labour_type_data = row.get("labour_types", {})
        if isinstance(labour_type_data, list) and len(labour_type_data) > 0:
            labour_type_data = labour_type_data[0]

        entry = {
            "labour_type_id": row.get("labour_type_id"),
            "labour_type_name": labour_type_data.get("name", ""),
            "rate_per_day": float(labour_type_data.get("rate_per_day", 0)),
            "count": int(row.get("count", 0)),
        }
        entry["amount"] = round(entry["count"] * entry["rate_per_day"], 2)

        if date not in by_date:
            by_date[date] = []
        by_date[date].append(entry)

    result = {"by_date": by_date}
    cache_set(redis, key, result, ttl=ttl)
    return result


@router.post("/daily")
def post_labour_daily(
    payload: LabourDailyCreateBody,
    access: dict = Depends(get_project_access_query(CAN_MANAGE_EXPENSE)),
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    from app.modules.labour.service import upsert_labour_daily
    from app.modules.labour.schemas import LabourDailyResponse

    project_id = access["project_id"]
    entries = upsert_labour_daily(
        supabase,
        project_id,
        payload.date,
        [e.model_dump() for e in payload.entries],
        current_user["id"],
        tenant_id,
    )
    return LabourDailyResponse(
        project_id=project_id,
        date=payload.date,
        entries=entries,
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
