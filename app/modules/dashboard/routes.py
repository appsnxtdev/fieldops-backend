from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_supabase_client, get_tenant_id, get_tenant_membership
from app.modules.dashboard.schemas import DashboardSummaryResponse
from app.modules.dashboard.service import get_dashboard_summary
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
