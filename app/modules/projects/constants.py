"""Project status constants and metadata."""
from enum import Enum
from typing import Literal, TypedDict


class ProjectStatus(str, Enum):
    """Project workflow status enum."""

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class StatusMetadata(TypedDict):
    """Status display metadata."""

    label: str
    color: str
    is_active: bool
    order: int


# Status metadata for UI rendering
STATUS_METADATA: dict[ProjectStatus, StatusMetadata] = {
    ProjectStatus.PLANNING: {
        "label": "Planning",
        "color": "#3b82f6",  # Blue
        "is_active": False,
        "order": 1,
    },
    ProjectStatus.ACTIVE: {
        "label": "Active",
        "color": "#10b981",  # Green
        "is_active": True,  # Only this counts as "active" for billing
        "order": 2,
    },
    ProjectStatus.ON_HOLD: {
        "label": "On Hold",
        "color": "#f59e0b",  # Amber
        "is_active": False,
        "order": 3,
    },
    ProjectStatus.COMPLETED: {
        "label": "Completed",
        "color": "#6366f1",  # Purple
        "is_active": False,
        "order": 4,
    },
    ProjectStatus.ARCHIVED: {
        "label": "Archived",
        "color": "#6b7280",  # Gray
        "is_active": False,
        "order": 5,
    },
}


ProjectHealth = Literal["on_track", "at_risk", "delayed"]
