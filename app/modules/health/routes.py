from fastapi import APIRouter

from app.modules.health.schemas import HealthResponse
from app.modules.health.service import get_health

router = APIRouter()


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    return get_health()
