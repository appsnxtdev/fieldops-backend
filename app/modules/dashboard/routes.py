from fastapi import APIRouter, Depends, Query

from app.core.cache import CacheKeys, cache_get, cache_set, get_redis_client
from app.core.dependencies import get_current_user, get_supabase_client, get_tenant_id, get_tenant_membership
from app.modules.dashboard.schemas import DashboardSummaryResponse, PeriodSummaryResponse
from app.modules.dashboard.service import get_dashboard_summary, get_period_summary
from supabase import Client

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    role = get_tenant_membership(tenant_id, current_user["id"], supabase, redis=redis)
    key = CacheKeys.dashboard(tenant_id, current_user["id"])
    cached = cache_get(redis, key)
    if cached is not None:
        return DashboardSummaryResponse(**cached)
    result = get_dashboard_summary(supabase, tenant_id, current_user["id"], tenant_role=role)
    cache_set(redis, key, result.model_dump(), ttl=90)
    return result


@router.get("/period-summary", response_model=PeriodSummaryResponse)
def period_summary(
    from_date: str = Query(..., description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., description="End date YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    role = get_tenant_membership(tenant_id, current_user["id"], supabase, redis=redis)
    key = CacheKeys.dashboard_period(tenant_id, current_user["id"], from_date, to_date)
    cached = cache_get(redis, key)
    if cached is not None:
        return PeriodSummaryResponse(**cached)
    result = get_period_summary(supabase, tenant_id, current_user["id"], role, from_date, to_date)
    cache_set(redis, key, result.model_dump(), ttl=60)
    return result
