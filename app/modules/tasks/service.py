import asyncio

from fastapi import HTTPException
from supabase import Client

from app.core.constants import DB_SCHEMA
from app.modules.notifications.triggers import (
    notify_task_assigned,
    notify_task_comment,
    notify_task_deleted,
    notify_task_status_changed,
)
from app.modules.projects.service import check_user_in_project
from app.modules.tasks.schemas import (
    TaskCreate,
    TaskResponse,
    TaskStatusCreate,
    TaskStatusResponse,
    TaskStatusUpdate,
    TaskUpdate,
    TaskUpdateNoteCreate,
    TaskUpdateNoteResponse,
)
from app.modules.users.service import get_profiles_by_ids


def list_statuses(supabase: Client, project_id: str) -> list[TaskStatusResponse]:
    r = supabase.schema(DB_SCHEMA).table("project_task_statuses").select("*").eq("project_id", project_id).order("sort_order").execute()
    return [TaskStatusResponse(**row) for row in (r.data or [])]


def create_status(supabase: Client, project_id: str, payload: TaskStatusCreate) -> TaskStatusResponse:
    row = {"project_id": project_id, "name": payload.name, "sort_order": payload.sort_order}
    r = supabase.schema(DB_SCHEMA).table("project_task_statuses").insert(row).execute()
    data = (r.data or [None])[0] if r else None
    if not data:
        raise ValueError("Insert did not return row")
    return TaskStatusResponse(**data)


def update_status(supabase: Client, status_id: str, project_id: str, payload: TaskStatusUpdate) -> TaskStatusResponse:
    data = payload.model_dump(exclude_unset=True)
    r = supabase.schema(DB_SCHEMA).table("project_task_statuses").update(data).eq("id", status_id).eq("project_id", project_id).execute()
    row = (r.data or [None])[0]
    if not row:
        raise ValueError("Task status not found")
    return TaskStatusResponse(**row)


def delete_status(supabase: Client, status_id: str, project_id: str) -> None:
    supabase.schema(DB_SCHEMA).table("project_task_statuses").delete().eq("id", status_id).eq("project_id", project_id).execute()


def _assignee_display_name(profile) -> str:
    if profile.full_name and profile.full_name.strip():
        return profile.full_name.strip()
    if profile.email and profile.email.strip():
        return profile.email.strip()
    return "Unknown"


def list_tasks(supabase: Client, project_id: str) -> list[TaskResponse]:
    r = supabase.schema(DB_SCHEMA).table("tasks").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
    rows = list(r.data or [])
    assignee_ids = list({row["assignee_id"] for row in rows if row.get("assignee_id")})
    profile_map = {}
    if assignee_ids:
        profiles = get_profiles_by_ids(supabase, assignee_ids)
        profile_map = {p.id: _assignee_display_name(p) for p in profiles}
    return [
        TaskResponse(
            **row,
            assignee_name=profile_map.get(row["assignee_id"]) if row.get("assignee_id") else None,
        )
        for row in rows
    ]


def get_task(supabase: Client, task_id: str, project_id: str) -> TaskResponse | None:
    r = supabase.schema(DB_SCHEMA).table("tasks").select("*").eq("id", task_id).eq("project_id", project_id).maybe_single().execute()
    if not r or not r.data:
        return None
    row = r.data[0] if isinstance(r.data, list) else r.data
    assignee_name = None
    if row.get("assignee_id"):
        profiles = get_profiles_by_ids(supabase, [row["assignee_id"]])
        if profiles:
            assignee_name = _assignee_display_name(profiles[0])
    return TaskResponse(**row, assignee_name=assignee_name)


def _task_response_with_assignee_name(supabase: Client, row: dict) -> TaskResponse:
    assignee_name = None
    if row.get("assignee_id"):
        profiles = get_profiles_by_ids(supabase, [row["assignee_id"]])
        if profiles:
            assignee_name = _assignee_display_name(profiles[0])
    return TaskResponse(**row, assignee_name=assignee_name)


async def create_task(supabase: Client, project_id: str, created_by: str, payload: TaskCreate) -> TaskResponse:
    # Validate assignee is a project member
    if payload.assignee_id:
        if not check_user_in_project(supabase, project_id, payload.assignee_id):
            raise HTTPException(
                status_code=400,
                detail="Assignee must be a member of the project"
            )

    row = {
        "project_id": project_id,
        "title": payload.title,
        "description": payload.description,
        "status_id": payload.status_id,
        "assignee_id": payload.assignee_id,
        "created_by": created_by,
        "due_at": payload.due_at,
    }
    r = supabase.schema(DB_SCHEMA).table("tasks").insert(row).execute()
    data = (r.data or [None])[0] if r else None
    if not data:
        raise ValueError("Insert did not return row")

    # Trigger notification if task is assigned
    if data.get('assignee_id'):
        # Get assigner name from profiles
        assigner_profiles = get_profiles_by_ids(supabase, [created_by])
        assigner_name = _assignee_display_name(assigner_profiles[0]) if assigner_profiles else 'Someone'

        # Get tenant_id from project
        proj_r = supabase.schema(DB_SCHEMA).table('projects').select('tenant_id').eq('id', project_id).single().execute()
        tenant_id = proj_r.data['tenant_id'] if proj_r and proj_r.data else None

        if tenant_id:
            await notify_task_assigned(
                supabase=supabase,
                task_id=data['id'],
                assignee_id=data['assignee_id'],
                assigner_id=created_by,
                assigner_name=assigner_name,
                task_title=data['title'],
                project_id=project_id,
                tenant_id=tenant_id,
            )

    return _task_response_with_assignee_name(supabase, data)


async def update_task(supabase: Client, task_id: str, project_id: str, payload: TaskUpdate) -> TaskResponse:
    # Validate assignee is a project member
    if payload.assignee_id:
        if not check_user_in_project(supabase, project_id, payload.assignee_id):
            raise HTTPException(
                status_code=400,
                detail="Assignee must be a member of the project"
            )

    # Fetch old task to detect status changes
    old_task_r = supabase.schema(DB_SCHEMA).table("tasks").select("*").eq("id", task_id).eq("project_id", project_id).maybe_single().execute()
    old_task = None
    if old_task_r and old_task_r.data:
        old_task = old_task_r.data[0] if isinstance(old_task_r.data, list) else old_task_r.data

    data = payload.model_dump(exclude_unset=True)
    r = supabase.schema(DB_SCHEMA).table("tasks").update(data).eq("id", task_id).eq("project_id", project_id).execute()
    row = (r.data or [None])[0]
    if not row:
        raise ValueError("Task not found")

    # Trigger notification if status changed
    if old_task and 'status_id' in data and data['status_id'] != old_task.get('status_id'):
        # Get status names
        old_status = 'Unknown'
        new_status = 'Unknown'
        if old_task.get('status_id'):
            old_status_r = supabase.schema(DB_SCHEMA).table('project_task_statuses').select('name').eq('id', old_task['status_id']).single().execute()
            if old_status_r and old_status_r.data:
                old_status = old_status_r.data['name']

        if row.get('status_id'):
            new_status_r = supabase.schema(DB_SCHEMA).table('project_task_statuses').select('name').eq('id', row['status_id']).single().execute()
            if new_status_r and new_status_r.data:
                new_status = new_status_r.data['name']

        # Get actor name - use created_by as fallback since we don't have current_user here
        actor_id = row.get('created_by', '')
        actor_profiles = get_profiles_by_ids(supabase, [actor_id]) if actor_id else []
        actor_name = _assignee_display_name(actor_profiles[0]) if actor_profiles else 'Someone'

        # Get tenant_id
        proj_r = supabase.schema(DB_SCHEMA).table('projects').select('tenant_id').eq('id', project_id).single().execute()
        tenant_id = proj_r.data['tenant_id'] if proj_r and proj_r.data else None

        if tenant_id:
            await notify_task_status_changed(
                supabase=supabase,
                task_id=task_id,
                task_title=row['title'],
                old_status=old_status,
                new_status=new_status,
                assignee_id=row.get('assignee_id'),
                assigner_id=row.get('created_by'),
                actor_id=actor_id,
                actor_name=actor_name,
                project_id=project_id,
                tenant_id=tenant_id,
            )

    return _task_response_with_assignee_name(supabase, row)


async def delete_task(supabase: Client, task_id: str, project_id: str, deleted_by: str) -> None:
    # Fetch task details before deletion for notification
    task_r = supabase.schema(DB_SCHEMA).table("tasks").select("*").eq("id", task_id).eq("project_id", project_id).maybe_single().execute()
    task = None
    if task_r and task_r.data:
        task = task_r.data[0] if isinstance(task_r.data, list) else task_r.data

    # Delete the task
    supabase.schema(DB_SCHEMA).table("tasks").delete().eq("id", task_id).eq("project_id", project_id).execute()

    # Send notification if task existed
    if task:
        # Get actor name
        actor_profiles = get_profiles_by_ids(supabase, [deleted_by])
        actor_name = _assignee_display_name(actor_profiles[0]) if actor_profiles else 'Someone'

        # Get tenant_id
        proj_r = supabase.schema(DB_SCHEMA).table('projects').select('tenant_id').eq('id', project_id).single().execute()
        tenant_id = proj_r.data['tenant_id'] if proj_r and proj_r.data else None

        if tenant_id:
            await notify_task_deleted(
                supabase=supabase,
                task_id=task_id,
                task_title=task['title'],
                assignee_id=task.get('assignee_id'),
                assigner_id=task.get('created_by'),
                actor_id=deleted_by,
                actor_name=actor_name,
                project_id=project_id,
                tenant_id=tenant_id,
            )


def list_task_updates(supabase: Client, project_id: str, task_id: str) -> list[TaskUpdateNoteResponse]:
    r = (
        supabase.schema(DB_SCHEMA)
        .table("task_updates")
        .select("*")
        .eq("task_id", task_id)
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = list(r.data or []) if r else []
    author_ids = list({row["author_id"] for row in rows if row.get("author_id")})
    profile_map = {}
    if author_ids:
        profiles = get_profiles_by_ids(supabase, author_ids)
        profile_map = {p.id: _assignee_display_name(p) for p in profiles}
    return [
        TaskUpdateNoteResponse(
            **row,
            author_name=profile_map.get(row["author_id"]) if row.get("author_id") else None,
        )
        for row in rows
    ]


async def add_task_update(supabase: Client, project_id: str, task_id: str, author_id: str, payload: TaskUpdateNoteCreate) -> TaskUpdateNoteResponse:
    note = (payload.note or "").strip()
    if not note:
        raise ValueError("Note is required")
    row = {"task_id": task_id, "project_id": project_id, "author_id": author_id, "note": note}
    r = supabase.schema(DB_SCHEMA).table("task_updates").insert(row).execute()
    data = (r.data or [None])[0] if r else None
    if not data:
        raise ValueError("Insert did not return row")
    author_name = None
    if author_id:
        profiles = get_profiles_by_ids(supabase, [author_id])
        if profiles:
            author_name = _assignee_display_name(profiles[0])

    # Get task details for notification
    task_r = supabase.schema(DB_SCHEMA).table("tasks").select("*").eq("id", task_id).single().execute()
    task = task_r.data if task_r else None

    if task:
        # Get author name for notification
        author_profiles = get_profiles_by_ids(supabase, [author_id])
        author_name_for_notif = _assignee_display_name(author_profiles[0]) if author_profiles else 'Someone'

        # Get tenant_id
        proj_r = supabase.schema(DB_SCHEMA).table('projects').select('tenant_id').eq('id', project_id).single().execute()
        tenant_id = proj_r.data['tenant_id'] if proj_r and proj_r.data else None

        if tenant_id:
            await notify_task_comment(
                supabase=supabase,
                task_id=task_id,
                task_title=task['title'],
                comment=note,
                assignee_id=task.get('assignee_id'),
                assigner_id=task.get('created_by'),
                actor_id=author_id,
                actor_name=author_name_for_notif,
                project_id=project_id,
                tenant_id=tenant_id,
            )

    return TaskUpdateNoteResponse(**data, author_name=author_name)


async def bulk_update_tasks(
    supabase: Client,
    task_ids: list[str],
    updates: dict,
    current_user_id: str,
) -> dict:
    """
    Update multiple tasks at once.

    Note: Does not send notifications for status changes. Use individual
    update_task for operations requiring notifications.

    Returns:
        {
            "updated": int,
            "failed": [{"task_id": str, "error": str}],
            "affected_projects": [str]
        }
    """
    updated_count = 0
    failed = []
    affected_projects = set()

    # Optimize: Batch fetch all tasks to avoid N+1 queries
    tasks_r = supabase.schema(DB_SCHEMA).table("tasks").select("id, project_id").in_("id", task_ids).execute()

    if not tasks_r or not tasks_r.data:
        return {
            "updated": 0,
            "failed": [{"task_id": tid, "error": "Task not found"} for tid in task_ids],
            "affected_projects": [],
        }

    # Build task_id -> project_id mapping
    task_map = {t["id"]: t["project_id"] for t in tasks_r.data}

    # Identify missing tasks
    missing = [tid for tid in task_ids if tid not in task_map]
    failed.extend([{"task_id": tid, "error": "Task not found"} for tid in missing])

    for task_id in task_ids:
        if task_id not in task_map:
            continue  # Already added to failed list

        try:
            project_id = task_map[task_id]

            # Check if user has permission to manage tasks in this project
            # First check if user is project member
            member_r = supabase.schema(DB_SCHEMA).table("project_members")\
                .select("role")\
                .eq("project_id", project_id)\
                .eq("user_id", current_user_id)\
                .maybe_single().execute()

            # If not a project member, check if they're an org_admin via tenant_members
            if not member_r or not member_r.data:
                # Get tenant_id from project
                proj_r = supabase.schema(DB_SCHEMA).table("projects")\
                    .select("tenant_id")\
                    .eq("id", project_id)\
                    .maybe_single().execute()

                if proj_r and proj_r.data:
                    project_data = proj_r.data[0] if isinstance(proj_r.data, list) else proj_r.data
                    tenant_id = project_data.get("tenant_id")

                    # Check if user is org_admin in tenant
                    tenant_r = supabase.schema(DB_SCHEMA).table("tenant_members")\
                        .select("role")\
                        .eq("tenant_id", tenant_id)\
                        .eq("user_id", current_user_id)\
                        .maybe_single().execute()

                    if not tenant_r or not tenant_r.data:
                        failed.append({"task_id": task_id, "error": "Permission denied"})
                        continue

                    tenant_data = tenant_r.data[0] if isinstance(tenant_r.data, list) else tenant_r.data
                    if tenant_data.get("role") != "org_admin":
                        failed.append({"task_id": task_id, "error": "Permission denied"})
                        continue
                else:
                    failed.append({"task_id": task_id, "error": "Permission denied"})
                    continue

            # Update the task
            r = supabase.schema(DB_SCHEMA).table("tasks").update(updates).eq("id", task_id).eq("project_id", project_id).execute()

            if r and r.data:
                updated_count += 1
                affected_projects.add(project_id)
            else:
                failed.append({"task_id": task_id, "error": "Update failed"})

        except Exception as e:
            failed.append({"task_id": task_id, "error": str(e)})

    return {
        "updated": updated_count,
        "failed": failed,
        "affected_projects": list(affected_projects),
    }


async def bulk_delete_tasks(
    supabase: Client,
    task_ids: list[str],
    current_user_id: str,
) -> dict:
    """
    Delete multiple tasks at once.

    Returns:
        {
            "deleted": int,
            "failed": [{"task_id": str, "error": str}],
            "affected_projects": [str]
        }
    """
    deleted_count = 0
    failed = []
    affected_projects = set()

    # Optimize: Batch fetch all tasks to avoid N+1 queries
    tasks_r = supabase.schema(DB_SCHEMA).table("tasks").select("id, project_id").in_("id", task_ids).execute()

    if not tasks_r or not tasks_r.data:
        return {
            "deleted": 0,
            "failed": [{"task_id": tid, "error": "Task not found"} for tid in task_ids],
            "affected_projects": [],
        }

    # Build task_id -> project_id mapping
    task_map = {t["id"]: t["project_id"] for t in tasks_r.data}

    # Identify missing tasks
    missing = [tid for tid in task_ids if tid not in task_map]
    failed.extend([{"task_id": tid, "error": "Task not found"} for tid in missing])

    for task_id in task_ids:
        if task_id not in task_map:
            continue  # Already added to failed list

        try:
            project_id = task_map[task_id]

            # Check if user has permission to manage tasks in this project
            # First check if user is project member
            member_r = supabase.schema(DB_SCHEMA).table("project_members")\
                .select("role")\
                .eq("project_id", project_id)\
                .eq("user_id", current_user_id)\
                .maybe_single().execute()

            # If not a project member, check if they're an org_admin via tenant_members
            if not member_r or not member_r.data:
                # Get tenant_id from project
                proj_r = supabase.schema(DB_SCHEMA).table("projects")\
                    .select("tenant_id")\
                    .eq("id", project_id)\
                    .maybe_single().execute()

                if proj_r and proj_r.data:
                    project_data = proj_r.data[0] if isinstance(proj_r.data, list) else proj_r.data
                    tenant_id = project_data.get("tenant_id")

                    # Check if user is org_admin in tenant
                    tenant_r = supabase.schema(DB_SCHEMA).table("tenant_members")\
                        .select("role")\
                        .eq("tenant_id", tenant_id)\
                        .eq("user_id", current_user_id)\
                        .maybe_single().execute()

                    if not tenant_r or not tenant_r.data:
                        failed.append({"task_id": task_id, "error": "Permission denied"})
                        continue

                    tenant_data = tenant_r.data[0] if isinstance(tenant_r.data, list) else tenant_r.data
                    if tenant_data.get("role") != "org_admin":
                        failed.append({"task_id": task_id, "error": "Permission denied"})
                        continue
                else:
                    failed.append({"task_id": task_id, "error": "Permission denied"})
                    continue

            # Delete using existing function (sends notifications)
            await delete_task(supabase, task_id, project_id, current_user_id)
            deleted_count += 1
            affected_projects.add(project_id)

        except Exception as e:
            failed.append({"task_id": task_id, "error": str(e)})

    return {
        "deleted": deleted_count,
        "failed": failed,
        "affected_projects": list(affected_projects),
    }
