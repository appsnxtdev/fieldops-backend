import logging

from supabase import Client

from app.modules.notifications.service import create_notification

logger = logging.getLogger(__name__)


async def notify_task_assigned(
    supabase: Client,
    task_id: str,
    assignee_id: str,
    assigner_id: str,
    assigner_name: str,
    task_title: str,
    project_id: str,
    tenant_id: str,
) -> None:
    """
    Trigger notification when task is assigned.

    Args:
        supabase: Supabase client
        task_id: Task ID
        assignee_id: User being assigned the task
        assigner_id: User who assigned the task
        assigner_name: Assigner's display name
        task_title: Task title
        project_id: Project ID
        tenant_id: Tenant ID
    """
    logger.info(f"Triggering task_assigned notification: task_id={task_id}, assignee={assignee_id}")
    await create_notification(
        supabase=supabase,
        tenant_id=tenant_id,
        user_id=assignee_id,
        actor_id=assigner_id,
        type='task_assigned',
        title='New Task Assigned',
        message=f'{assigner_name} assigned you a task: {task_title}',
        entity_type='task',
        entity_id=task_id,
        project_id=project_id,
        metadata={
            'actor_name': assigner_name,
            'task_title': task_title,
        },
    )
    logger.info(f"Successfully created task_assigned notification for user={assignee_id}")


async def notify_task_status_changed(
    supabase: Client,
    task_id: str,
    task_title: str,
    old_status: str,
    new_status: str,
    assignee_id: str | None,
    assigner_id: str | None,
    actor_id: str,
    actor_name: str,
    project_id: str,
    tenant_id: str,
) -> None:
    """
    Trigger notification when task status changes.

    Notifies the OTHER person (not the actor).

    Args:
        supabase: Supabase client
        task_id: Task ID
        task_title: Task title
        old_status: Previous status name
        new_status: New status name
        assignee_id: Task assignee ID
        assigner_id: Task creator ID
        actor_id: User who changed the status
        actor_name: Actor's display name
        project_id: Project ID
        tenant_id: Tenant ID
    """
    logger.info(f"Triggering task_status_changed notification: task_id={task_id}, old={old_status}, new={new_status}")
    # Determine recipient (the OTHER person, not the actor)
    recipient_id = None
    if actor_id == assignee_id and assigner_id:
        recipient_id = assigner_id
    elif actor_id == assigner_id and assignee_id:
        recipient_id = assignee_id

    if not recipient_id:
        logger.warning(f"No recipient for task_status_changed: task_id={task_id}")
        return  # No one to notify

    await create_notification(
        supabase=supabase,
        tenant_id=tenant_id,
        user_id=recipient_id,
        actor_id=actor_id,
        type='task_status_changed',
        title='Task Status Changed',
        message=f'{actor_name} marked "{task_title}" as {new_status}',
        entity_type='task',
        entity_id=task_id,
        project_id=project_id,
        metadata={
            'actor_name': actor_name,
            'task_title': task_title,
            'old_status': old_status,
            'new_status': new_status,
        },
    )
    logger.info(f"Successfully created task_status_changed notification for user={recipient_id}")


async def notify_task_comment(
    supabase: Client,
    task_id: str,
    task_title: str,
    comment: str,
    assignee_id: str | None,
    assigner_id: str | None,
    actor_id: str,
    actor_name: str,
    project_id: str,
    tenant_id: str,
) -> None:
    """
    Trigger notification when comment is added to task.

    Notifies the OTHER person (not the actor).

    Args:
        supabase: Supabase client
        task_id: Task ID
        task_title: Task title
        comment: Comment text
        assignee_id: Task assignee ID
        assigner_id: Task creator ID
        actor_id: User who added the comment
        actor_name: Actor's display name
        project_id: Project ID
        tenant_id: Tenant ID
    """
    logger.info(f"Triggering task_comment_added notification: task_id={task_id}, actor={actor_id}")
    # Determine recipient (the OTHER person, not the actor)
    recipient_id = None
    if actor_id == assignee_id and assigner_id:
        recipient_id = assigner_id
    elif actor_id == assigner_id and assignee_id:
        recipient_id = assignee_id

    if not recipient_id:
        logger.warning(f"No recipient for task_comment_added: task_id={task_id}")
        return  # No one to notify

    await create_notification(
        supabase=supabase,
        tenant_id=tenant_id,
        user_id=recipient_id,
        actor_id=actor_id,
        type='task_comment_added',
        title='New Comment',
        message=f'{actor_name} commented on "{task_title}"',
        entity_type='task',
        entity_id=task_id,
        project_id=project_id,
        metadata={
            'actor_name': actor_name,
            'task_title': task_title,
            'comment_preview': comment[:100],
        },
    )
    logger.info(f"Successfully created task_comment_added notification for user={recipient_id}")


async def notify_task_deleted(
    supabase: Client,
    task_id: str,
    task_title: str,
    assignee_id: str | None,
    assigner_id: str | None,
    actor_id: str,
    actor_name: str,
    project_id: str,
    tenant_id: str,
) -> None:
    """
    Trigger notification when a task is deleted.

    Notifies both the assignee and the creator (if different from the actor).

    Args:
        supabase: Supabase client
        task_id: Task ID (will be used for entity_id even though deleted)
        task_title: Task title
        assignee_id: Task assignee ID
        assigner_id: Task creator ID
        actor_id: User who deleted the task
        actor_name: Actor's display name
        project_id: Project ID
        tenant_id: Tenant ID
    """
    logger.info(f"Triggering task_deleted notification: task_id={task_id}, actor={actor_id}")

    # Collect recipients (both assignee and creator, but not the actor)
    recipients = set()
    if assignee_id and assignee_id != actor_id:
        recipients.add(assignee_id)
    if assigner_id and assigner_id != actor_id:
        recipients.add(assigner_id)

    if not recipients:
        logger.warning(f"No recipients for task_deleted: task_id={task_id}")
        return  # No one to notify

    # Send notification to all recipients
    for recipient_id in recipients:
        await create_notification(
            supabase=supabase,
            tenant_id=tenant_id,
            user_id=recipient_id,
            actor_id=actor_id,
            type='task_deleted',
            title='Task Deleted',
            message=f'{actor_name} deleted the task: {task_title}',
            entity_type='task',
            entity_id=task_id,
            project_id=project_id,
            metadata={
                'actor_name': actor_name,
                'task_title': task_title,
            },
        )
        logger.info(f"Successfully created task_deleted notification for user={recipient_id}")
