from fastapi import APIRouter, Depends, Query

from app.core.cache import DEMO_CACHE_TTL, CacheKeys, cache_get, cache_set, get_redis_client, is_demo_user
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

    # Cache for org_admin and demo users (demo gets 7-day persistent cache)
    should_cache = role == "org_admin" or is_demo_user(role)

    if should_cache:
        if is_demo_user(role):
            key = CacheKeys.demo_dashboard(tenant_id)
            ttl = DEMO_CACHE_TTL
        else:
            key = CacheKeys.dashboard(tenant_id, current_user["id"])
            ttl = 90

        cached = cache_get(redis, key)
        if cached is not None:
            return DashboardSummaryResponse(**cached)

    result = get_dashboard_summary(supabase, tenant_id, current_user["id"], tenant_role=role)

    if should_cache:
        cache_set(redis, key, result.model_dump(), ttl=ttl)

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

    # Cache for org_admin and demo users (demo gets 7-day persistent cache)
    should_cache = role == "org_admin" or is_demo_user(role)

    if should_cache:
        if is_demo_user(role):
            key = CacheKeys.demo_dashboard_period(tenant_id, from_date, to_date)
            ttl = DEMO_CACHE_TTL
        else:
            key = CacheKeys.dashboard_period(tenant_id, current_user["id"], from_date, to_date)
            ttl = 60

        cached = cache_get(redis, key)
        if cached is not None:
            return PeriodSummaryResponse(**cached)

    result = get_period_summary(supabase, tenant_id, current_user["id"], role, from_date, to_date)

    if should_cache:
        cache_set(redis, key, result.model_dump(), ttl=ttl)

    return result
