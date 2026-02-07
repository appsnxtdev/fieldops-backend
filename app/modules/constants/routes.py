from fastapi import APIRouter, Depends

from app.core.constants import MATERIAL_UNITS
from app.core.dependencies import get_tenant_id

router = APIRouter()


@router.get("/material-units")
def get_material_units(
    _: str = Depends(get_tenant_id),
) -> list[str]:
    """Return the fixed list of allowed material units (tenant auth required)."""
    return list(MATERIAL_UNITS)
