from fastapi import APIRouter, Depends, Query

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
):
    role = get_tenant_membership(tenant_id, current_user["id"], supabase)
    return get_dashboard_summary(supabase, tenant_id, current_user["id"], tenant_role=role)


@router.get("/period-summary", response_model=PeriodSummaryResponse)
def period_summary(
    from_date: str = Query(..., description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., description="End date YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    role = get_tenant_membership(tenant_id, current_user["id"], supabase)
    return get_period_summary(
        supabase, tenant_id, current_user["id"], role, from_date, to_date
    )
