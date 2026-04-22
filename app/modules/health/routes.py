from fastapi import APIRouter, Depends, HTTPException

from app.core.constants import DB_SCHEMA
from app.core.dependencies import get_supabase_client
from app.modules.health.schemas import HealthResponse
from app.modules.health.service import get_health
from supabase import Client

router = APIRouter()


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    return get_health()


@router.get("/ready")
def ready(supabase: Client = Depends(get_supabase_client)) -> dict:
    try:
        supabase.schema(DB_SCHEMA).table("projects").select("id").limit(1).execute()
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
