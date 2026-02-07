from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_tenant_id
from app.modules.tenants.schemas import TenantResponse
from app.modules.tenants.service import get_tenant_details

router = APIRouter()


@router.get("/me", response_model=TenantResponse)
def get_my_tenant(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
):
    details = get_tenant_details(tenant_id, current_user.get("app_metadata"))
    return TenantResponse(id=details["id"], name=details.get("name"))
