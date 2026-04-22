import logging
from datetime import datetime
from typing import Literal

from supabase import Client

from app.core.constants import DB_SCHEMA
from app.core.firebase import send_fcm_message
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationResponse,
    NotificationType,
)

logger = logging.getLogger(__name__)


async def create_notification(
    supabase: Client,
    tenant_id: str,
    user_id: str,
    actor_id: str,
    type: NotificationType,
    title: str,
    message: str,
    entity_type: str,
    entity_id: str,
    project_id: str | None,
    metadata: dict | None,
) -> dict:
    """
    Create a notification record and send FCM push.

    Args:
        supabase: Supabase client
        tenant_id: Tenant ID
        user_id: Recipient user ID
        actor_id: User who performed the action
        type: Notification type
        title: Notification title
        message: Notification message
        entity_type: Entity type (e.g., 'task')
        entity_id: Entity ID
        project_id: Optional project ID
        metadata: Optional metadata dict

    Returns:
        Created notification record
    """
    logger.info(f"Creating notification: type={type}, user={user_id}, entity={entity_id}")

    row = {
        'tenant_id': tenant_id,
        'user_id': user_id,
        'actor_id': actor_id,
        'type': type,
        'title': title,
        'message': message,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'project_id': project_id,
        'metadata': metadata,
    }

    r = supabase.schema(DB_SCHEMA).table('notifications').insert(row).execute()
    data = (r.data or [None])[0] if r else None
    if not data:
        logger.error(f"Notification insert failed: user={user_id}, type={type}")
        raise ValueError("Notification insert did not return row")

    logger.info(f"Notification created: id={data['id']}, user={user_id}")

    # Send FCM push asynchronously (don't block on failure)
    try:
        logger.info(f"Sending FCM push: notification_id={data['id']}")
        await send_fcm_push(supabase, user_id, title, message, {
            'type': type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'notification_id': data['id'],
            'action': 'sync'
        })
        logger.info(f"FCM push sent successfully: notification_id={data['id']}")
    except Exception as e:
        logger.error(f"FCM push failed: notification_id={data['id']}, error={e}")
        # Don't re-raise - notification is already saved

    return data


async def send_fcm_push(
    supabase: Client,
    user_id: str,
    title: str,
    body: str,
    data: dict,
) -> None:
    """
    Send FCM push notification to user's active devices.

    Args:
        supabase: Supabase client
        user_id: User ID
        title: Push notification title
        body: Push notification body
        data: Custom data payload
    """
    # Get user's active FCM tokens
    r = supabase.schema(DB_SCHEMA).table('user_devices') \
        .select('fcm_token') \
        .eq('user_id', user_id) \
        .eq('is_active', True) \
        .execute()

    tokens = [row['fcm_token'] for row in (r.data or [])]

    if not tokens:
        logger.info(f"No active FCM tokens for user {user_id}")
        return

    # Send to all devices
    for token in tokens:
        success = await send_fcm_message(token, title, body, data)

        # Mark token as inactive if invalid
        if not success:
            try:
                supabase.schema(DB_SCHEMA).table('user_devices') \
                    .update({'is_active': False}) \
                    .eq('fcm_token', token) \
                    .execute()
            except Exception as e:
                logger.error(f"Failed to mark token as inactive: {e}")


def get_user_notifications(
    supabase: Client,
    user_id: str,
    tenant_id: str,
    limit: int = 50,
    offset: int = 0,
) -> NotificationListResponse:
    """
    Fetch paginated notifications for a user.

    Args:
        supabase: Supabase client
        user_id: User ID
        tenant_id: Tenant ID
        limit: Page size
        offset: Page offset

    Returns:
        NotificationListResponse with notifications, total, and unread_count
    """
    # Fetch notifications
    r = supabase.schema(DB_SCHEMA).table('notifications') \
        .select('*') \
        .eq('user_id', user_id) \
        .eq('tenant_id', tenant_id) \
        .order('created_at', desc=True) \
        .limit(limit) \
        .offset(offset) \
        .execute()

    notifications = [NotificationResponse(**row) for row in (r.data or [])]

    # Get total count
    count_r = supabase.schema(DB_SCHEMA).table('notifications') \
        .select('id', count='exact') \
        .eq('user_id', user_id) \
        .eq('tenant_id', tenant_id) \
        .execute()

    total = count_r.count if count_r else 0

    # Get unread count
    unread_r = supabase.schema(DB_SCHEMA).table('notifications') \
        .select('id', count='exact') \
        .eq('user_id', user_id) \
        .eq('tenant_id', tenant_id) \
        .eq('is_read', False) \
        .execute()

    unread_count = unread_r.count if unread_r else 0

    return NotificationListResponse(
        notifications=notifications,
        total=total,
        unread_count=unread_count,
    )


def get_unread_count(supabase: Client, user_id: str, tenant_id: str) -> int:
    """Get count of unread notifications for a user."""
    r = supabase.schema(DB_SCHEMA).table('notifications') \
        .select('id', count='exact') \
        .eq('user_id', user_id) \
        .eq('tenant_id', tenant_id) \
        .eq('is_read', False) \
        .execute()

    return r.count if r else 0


def mark_as_read(supabase: Client, user_id: str, notification_id: str) -> None:
    """Mark a single notification as read."""
    supabase.schema(DB_SCHEMA).table('notifications') \
        .update({'is_read': True, 'read_at': datetime.utcnow().isoformat()}) \
        .eq('id', notification_id) \
        .eq('user_id', user_id) \
        .execute()


def mark_all_as_read(supabase: Client, user_id: str, tenant_id: str) -> None:
    """Mark all user notifications as read."""
    supabase.schema(DB_SCHEMA).table('notifications') \
        .update({'is_read': True, 'read_at': datetime.utcnow().isoformat()}) \
        .eq('user_id', user_id) \
        .eq('tenant_id', tenant_id) \
        .eq('is_read', False) \
        .execute()


def register_device(
    supabase: Client,
    user_id: str,
    fcm_token: str,
    platform: Literal['android', 'ios'],
    device_id: str | None,
) -> None:
    """
    Register or update user's FCM token.

    Args:
        supabase: Supabase client
        user_id: User ID
        fcm_token: FCM device token
        platform: Platform (android or ios)
        device_id: Optional device identifier
    """
    row = {
        'user_id': user_id,
        'fcm_token': fcm_token,
        'platform': platform,
        'device_id': device_id,
        'is_active': True,
        'updated_at': datetime.utcnow().isoformat(),
    }

    # Upsert (insert or update on conflict)
    supabase.schema(DB_SCHEMA).table('user_devices').upsert(row, on_conflict='user_id,fcm_token').execute()


def unregister_device(supabase: Client, user_id: str, fcm_token: str) -> None:
    """
    Mark device as inactive.

    Args:
        supabase: Supabase client
        user_id: User ID
        fcm_token: FCM token to deactivate
    """
    supabase.schema(DB_SCHEMA).table('user_devices') \
        .update({'is_active': False}) \
        .eq('user_id', user_id) \
        .eq('fcm_token', fcm_token) \
        .execute()
