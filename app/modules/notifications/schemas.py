from typing import Literal

from pydantic import BaseModel

NotificationType = Literal['task_assigned', 'task_status_changed', 'task_comment_added', 'task_deleted']


class NotificationResponse(BaseModel):
    """Notification response model."""

    id: str
    tenant_id: str
    user_id: str
    actor_id: str
    type: NotificationType
    title: str
    message: str
    entity_type: str
    entity_id: str
    project_id: str | None
    metadata: dict | None
    is_read: bool
    created_at: str
    read_at: str | None


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""

    notifications: list[NotificationResponse]
    total: int
    unread_count: int


class MarkReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: list[str] | None = None  # None = mark all


class FCMTokenRequest(BaseModel):
    """Request to register FCM token."""

    fcm_token: str
    platform: Literal['android', 'ios']
    device_id: str | None = None
