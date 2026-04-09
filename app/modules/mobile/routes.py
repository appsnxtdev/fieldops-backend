"""Routes for mobile endpoints."""
from fastapi import APIRouter, Depends
from supabase import Client

from app.core.dependencies import get_supabase_client, get_current_user, get_redis_client
from app.core.cache import cache_delete, CacheKeys
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
    service = MobileService(supabase)
    response = await service.get_bulk_sync_data(current_user["id"], tenant_id)

    # Invalidate expense cache for all projects to ensure fresh wallet data
    cache_keys_to_delete = []
    for project in response.projects:
        cache_keys_to_delete.append(CacheKeys.expense(project.id))

    if cache_keys_to_delete:
        cache_delete(redis, *cache_keys_to_delete)

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


@router.post("/sync-queue", response_model=SyncQueueResponse)
async def sync_queue(
    request: SyncQueueRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Process batch of queued changes."""
    tenant_id = (current_user.get("app_metadata") or {}).get("tenant_id")
    service = MobileService(supabase)
    return await service.process_sync_queue(
        current_user["id"],
        tenant_id,
        [change.model_dump() for change in request.changes]
    )
