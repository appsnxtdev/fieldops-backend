from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user, get_project_access, get_supabase_client
from app.core.permissions import CAN_MANAGE_TASK_STATUSES, CAN_MANAGE_TASKS, CAN_VIEW_PROJECT
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
from app.modules.tasks.service import (
    add_task_update,
    create_status,
    create_task,
    delete_status,
    delete_task,
    get_task,
    list_statuses,
    list_tasks,
    list_task_updates,
    update_status,
    update_task,
)
from supabase import Client

router = APIRouter()


@router.get("/{project_id}/statuses", response_model=list[TaskStatusResponse])
def list_statuses_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    return list_statuses(supabase, project_id)


@router.post("/{project_id}/statuses", response_model=TaskStatusResponse, status_code=201)
def create_status_route(
    project_id: str,
    payload: TaskStatusCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_TASK_STATUSES)),
    supabase: Client = Depends(get_supabase_client),
):
    return create_status(supabase, project_id, payload)


@router.patch("/{project_id}/statuses/{status_id}", response_model=TaskStatusResponse)
def update_status_route(
    project_id: str,
    status_id: str,
    payload: TaskStatusUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_TASK_STATUSES)),
    supabase: Client = Depends(get_supabase_client),
):
    return update_status(supabase, status_id, project_id, payload)


@router.delete("/{project_id}/statuses/{status_id}", status_code=204)
def delete_status_route(
    project_id: str,
    status_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_TASK_STATUSES)),
    supabase: Client = Depends(get_supabase_client),
):
    delete_status(supabase, status_id, project_id)


@router.get("/{project_id}/tasks", response_model=list[TaskResponse])
def list_tasks_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    return list_tasks(supabase, project_id)


@router.get("/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def get_task_route(
    project_id: str,
    task_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    t = get_task(supabase, task_id, project_id)
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    return t


@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=201)
def create_task_route(
    project_id: str,
    payload: TaskCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_TASKS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    return create_task(supabase, project_id, current_user["id"], payload)


@router.patch("/{project_id}/tasks/{task_id}", response_model=TaskResponse)
def update_task_route(
    project_id: str,
    task_id: str,
    payload: TaskUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_TASKS)),
    supabase: Client = Depends(get_supabase_client),
):
    return update_task(supabase, task_id, project_id, payload)


@router.delete("/{project_id}/tasks/{task_id}", status_code=204)
def delete_task_route(
    project_id: str,
    task_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_TASKS)),
    supabase: Client = Depends(get_supabase_client),
):
    delete_task(supabase, task_id, project_id)


@router.get("/{project_id}/tasks/{task_id}/updates", response_model=list[TaskUpdateNoteResponse])
def list_task_updates_route(
    project_id: str,
    task_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    return list_task_updates(supabase, project_id, task_id)


@router.post("/{project_id}/tasks/{task_id}/updates", response_model=TaskUpdateNoteResponse, status_code=201)
def add_task_update_route(
    project_id: str,
    task_id: str,
    payload: TaskUpdateNoteCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_TASKS)),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    return add_task_update(supabase, project_id, task_id, current_user["id"], payload)
