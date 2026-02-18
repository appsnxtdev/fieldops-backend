from supabase import Client

from app.core.constants import DB_SCHEMA
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


def create_task(supabase: Client, project_id: str, created_by: str, payload: TaskCreate) -> TaskResponse:
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
    return _task_response_with_assignee_name(supabase, data)


def update_task(supabase: Client, task_id: str, project_id: str, payload: TaskUpdate) -> TaskResponse:
    data = payload.model_dump(exclude_unset=True)
    r = supabase.schema(DB_SCHEMA).table("tasks").update(data).eq("id", task_id).eq("project_id", project_id).execute()
    row = (r.data or [None])[0]
    if not row:
        raise ValueError("Task not found")
    return _task_response_with_assignee_name(supabase, row)


def delete_task(supabase: Client, task_id: str, project_id: str) -> None:
    supabase.schema(DB_SCHEMA).table("tasks").delete().eq("id", task_id).eq("project_id", project_id).execute()


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
    return [TaskUpdateNoteResponse(**row) for row in (r.data or [])] if r else []


def add_task_update(supabase: Client, project_id: str, task_id: str, author_id: str, payload: TaskUpdateNoteCreate) -> TaskUpdateNoteResponse:
    note = (payload.note or "").strip()
    if not note:
        raise ValueError("Note is required")
    row = {"task_id": task_id, "project_id": project_id, "author_id": author_id, "note": note}
    r = supabase.schema(DB_SCHEMA).table("task_updates").insert(row).execute()
    data = (r.data or [None])[0] if r else None
    if not data:
        raise ValueError("Insert did not return row")
    return TaskUpdateNoteResponse(**data)
