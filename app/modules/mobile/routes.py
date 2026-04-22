"""Routes for mobile endpoints."""
from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import get_supabase_client, get_current_user, get_redis_client
from app.core.cache import cache_delete, cache_get, cache_set, CacheKeys
from .schemas import (
    BulkSyncResponse,
    MasterDataResponse,
    SyncQueueRequest,
    SyncQueueResponse,
)
from .service import MobileService

router = APIRouter(tags=["mobile"])


@router.get("/bulk-sync", response_model=BulkSyncResponse)
async def bulk_sync(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    """Get all mobile data in one call."""
    tenant_id = (current_user.get("app_metadata") or {}).get("tenant_id")
    user_id = current_user["id"]

    # Check cache first
    cache_key = CacheKeys.bulk_sync(user_id, tenant_id)
    cached = cache_get(redis, cache_key)
    if cached:
        return BulkSyncResponse(**cached)

    # Fetch fresh data
    service = MobileService(supabase)
    response = await service.get_bulk_sync_data(user_id, tenant_id)

    # Cache for 60 seconds
    cache_set(redis, cache_key, response.model_dump(), ttl=60)

    return response


@router.get("/master-data", response_model=MasterDataResponse)
async def master_data(
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Get master data (labour types, materials)."""
    tenant_id = (current_user.get("app_metadata") or {}).get("tenant_id")
    service = MobileService(supabase)
    return await service.get_master_data(tenant_id)


@router.get("/attendance/{project_id}")
async def get_attendance_today(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Get today's attendance for a project (never cached, always real-time)."""
    from datetime import datetime, timezone
    from .schemas import AttendanceToday

    user_id = current_user["id"]
    today = datetime.now(timezone.utc).date().isoformat()

    service = MobileService(supabase)
    attendance = await service._get_attendance_today(project_id, user_id, today)

    return attendance


@router.get("/wallet/{project_id}")
async def get_wallet(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Get wallet balance and recent transactions for a project (never cached, always real-time)."""
    from datetime import datetime, timezone
    from .schemas import Wallet

    today = datetime.now(timezone.utc).date().isoformat()

    service = MobileService(supabase)
    wallet = await service._get_wallet(project_id, today)

    return wallet


@router.post("/sync-queue", response_model=SyncQueueResponse)
async def sync_queue(
    request: SyncQueueRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
    redis=Depends(get_redis_client),
):
    """Process batch of queued changes."""
    tenant_id = (current_user.get("app_metadata") or {}).get("tenant_id")
    service = MobileService(supabase)
    result = await service.process_sync_queue(
        current_user["id"],
        tenant_id,
        [change.model_dump() for change in request.changes]
    )

    # Invalidate bulk-sync cache after processing changes
    cache_delete(redis, CacheKeys.bulk_sync(current_user["id"], tenant_id))

    return result
