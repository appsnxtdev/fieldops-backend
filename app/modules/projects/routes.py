from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user, get_project_access, get_supabase_client, get_tenant_id, require_tenant_org_admin
from app.core.permissions import CAN_MANAGE_MEMBERS, CAN_MANAGE_PROJECT, CAN_VIEW_PROJECT
from app.modules.projects.schemas import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectMyAccessResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.modules.projects.service import (
    add_project_member,
    create_project,
    delete_project,
    get_project,
    list_project_members,
    list_projects,
    remove_project_member,
    update_project,
    update_project_member,
)
from supabase import Client

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
def list_my_projects(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    return list_projects(supabase, tenant_id, current_user["id"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project_route(
    payload: ProjectCreate,
    tenant_id: str = Depends(require_tenant_org_admin),
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    return create_project(supabase, tenant_id, payload, current_user["id"])


@router.get("/{project_id}/my-access", response_model=ProjectMyAccessResponse)
def get_my_project_access(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
):
    return ProjectMyAccessResponse(role=access["role"])


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_VIEW_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    proj = get_project(supabase, project_id, access["tenant_id"])
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project_route(
    project_id: str,
    payload: ProjectUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    return update_project(supabase, project_id, access["tenant_id"], payload)


@router.put("/{project_id}", response_model=ProjectResponse)
def put_project_route(
    project_id: str,
    payload: ProjectUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    return update_project(supabase, project_id, access["tenant_id"], payload, full_replace=True)


@router.delete("/{project_id}", status_code=204)
def delete_project_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_PROJECT)),
    supabase: Client = Depends(get_supabase_client),
):
    delete_project(supabase, project_id, access["tenant_id"])


# Project members (nested under projects)
@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def list_members_route(
    project_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    return list_project_members(supabase, project_id)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=201)
def add_member_route(
    project_id: str,
    payload: ProjectMemberCreate,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    return add_project_member(supabase, project_id, payload)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def update_member_route(
    project_id: str,
    user_id: str,
    payload: ProjectMemberUpdate,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    return update_project_member(supabase, project_id, user_id, payload.role)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member_route(
    project_id: str,
    user_id: str,
    access: dict = Depends(get_project_access(CAN_MANAGE_MEMBERS)),
    supabase: Client = Depends(get_supabase_client),
):
    remove_project_member(supabase, project_id, user_id)
