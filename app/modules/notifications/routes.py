from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_supabase_client, get_tenant_id
from app.modules.notifications.schemas import (
    FCMTokenRequest,
    NotificationListResponse,
)
from app.modules.notifications.service import (
    get_unread_count,
    get_user_notifications,
    mark_all_as_read,
    mark_as_read,
    register_device,
)
from supabase import Client

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    """List user's notifications (paginated, newest first)."""
    return get_user_notifications(
        supabase,
        current_user['id'],
        tenant_id,
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count")
def get_unread_count_endpoint(
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    """Get count of unread notifications."""
    count = get_unread_count(supabase, current_user['id'], tenant_id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Mark a single notification as read."""
    mark_as_read(supabase, current_user['id'], notification_id)
    return {"status": "ok"}


@router.post("/mark-all-read")
def mark_all_read_endpoint(
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    supabase: Client = Depends(get_supabase_client),
):
    """Mark all user notifications as read."""
    mark_all_as_read(supabase, current_user['id'], tenant_id)
    return {"status": "ok"}


@router.post("/register-device")
def register_device_endpoint(
    request: FCMTokenRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Register user's device for push notifications."""
    register_device(
        supabase,
        current_user['id'],
        request.fcm_token,
        request.platform,
        request.device_id,
    )
    return {"status": "ok"}
