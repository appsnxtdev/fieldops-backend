from fastapi import APIRouter, Depends

from app.core.constants import DONE_TASK_STATUS_NAMES, MATERIAL_UNITS
from app.core.dependencies import get_tenant_id

router = APIRouter()


@router.get("/material-units")
def get_material_units(
    _: str = Depends(get_tenant_id),
) -> list[str]:
    """Return the fixed list of allowed material units (tenant auth required)."""
    return list(MATERIAL_UNITS)


@router.get("/done-task-status-names")
def get_done_task_status_names(
    _: str = Depends(get_tenant_id),
) -> list[str]:
    """Return task status names that count as done (for dashboard metrics)."""
    return list(DONE_TASK_STATUS_NAMES)
