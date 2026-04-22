from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, field_validator

from app.modules.projects.constants import ProjectStatus, ProjectHealth


class ProjectCreate(BaseModel):
    name: str
    timezone: str = "Asia/Kolkata"
    lat: float | None = None
    lng: float | None = None
    location: str | None = None
    address: str | None = None
    project_admin_user_id: str | None = None
    # Lifecycle management fields
    status: str = "planning"
    project_owner_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    estimated_completion_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is a valid ProjectStatus enum value."""
        valid_statuses = [status.value for status in ProjectStatus]
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(valid_statuses)}"
            )
        return v


class ProjectUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None
    lat: float | None = None
    lng: float | None = None
    location: str | None = None
    address: str | None = None
    project_admin_user_id: str | None = None
    # Lifecycle management fields
    status: str | None = None
    project_owner_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    estimated_completion_date: date | None = None
    actual_completion_date: date | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is a valid ProjectStatus enum value."""
        if v is None:
            return v
        valid_statuses = [status.value for status in ProjectStatus]
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(valid_statuses)}"
            )
        return v


class ProjectResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    timezone: str
    lat: float | None = None
    lng: float | None = None
    location: str | None = None
    address: str | None = None
    project_admin_user_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    # Lifecycle management fields
    status: str = "planning"
    project_owner_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    estimated_completion_date: date | None = None
    actual_completion_date: date | None = None
    # Computed fields (populated by service layer)
    status_info: Optional["ProjectStatusInfo"] = None
    project_owner: Optional["UserBasicInfo"] = None
    health: Optional[ProjectHealth] = None
    progress_percentage: float | None = None
    is_out_of_date: bool = False
    last_activity_at: str | None = None


class ProjectMemberCreate(BaseModel):
    user_id: str
    role: str  # admin | member | viewer


class ProjectMemberUpdate(BaseModel):
    role: str


class ProjectMemberResponse(BaseModel):
    project_id: str
    user_id: str
    role: str
    created_at: str | None = None
    # User info for UI display (populated by service layer)
    user_email: str | None = None
    user_full_name: str | None = None
    user_avatar_url: str | None = None


class ProjectMyAccessResponse(BaseModel):
    role: str  # admin | member | viewer


# Lifecycle management schemas

class ProjectStatusInfo(BaseModel):
    """Status metadata for UI rendering."""

    label: str
    color: str
    is_active: bool


class UserBasicInfo(BaseModel):
    """Basic user information for project responses."""

    id: str
    email: str
    full_name: str | None = None


class ProjectUpdateNoteCreate(BaseModel):
    """Schema for creating a project update note."""

    note: str


class ProjectUpdateNoteResponse(BaseModel):
    """Schema for project update note responses."""

    id: str
    project_id: str
    author_id: str
    author: UserBasicInfo
    note: str
    created_at: str | None


class ProjectStatusUpdateRequest(BaseModel):
    """Schema for updating project status."""

    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is a valid ProjectStatus enum value."""
        valid_statuses = [status.value for status in ProjectStatus]
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(valid_statuses)}"
            )
        return v
