from typing import Literal

from pydantic import BaseModel

ProjectHealth = Literal["on_track", "at_risk", "delayed"]
ProjectWorkflowStatus = Literal["planning", "active", "on_hold", "completed", "archived"]
AlertLevel = Literal["low"]


class ProjectSummaryItem(BaseModel):
    project_id: str
    project_name: str
    location: str | None = None
    lat: float | None = None
    lng: float | None = None
    wallet_balance: float = 0
    task_count: int = 0
    due_tasks: int = 0
    today_attendance_count: int = 0
    # Lifecycle management fields
    workflow_status: ProjectWorkflowStatus = "planning"
    health: ProjectHealth | None = None
    task_completion_percentage: float = 0.0
    material_alerts: int = 0
    is_out_of_date: bool = False
    last_activity_at: str | None = None
    project_admin_user_id: str | None = None
    project_admin_name: str | None = None


class ComparisonSnapshot(BaseModel):
    """Historical dashboard metrics snapshot for comparative analysis."""

    total_sites: int
    total_wallet_balance: float
    total_tasks: int
    total_today_present: int


class DashboardSummaryResponse(BaseModel):
    projects: list[ProjectSummaryItem]
    total_sites: int = 0
    total_today_present: int = 0
    total_wallet_balance: float = 0
    total_tasks: int = 0
    total_due_tasks: int = 0
    # NEW: Comparative snapshots
    yesterday_snapshot: ComparisonSnapshot | None = None
    last_week_snapshot: ComparisonSnapshot | None = None
    last_month_snapshot: ComparisonSnapshot | None = None
    material_alerts_count: int = 0
    # NEW: Health distribution totals
    projects_on_track_count: int = 0
    projects_at_risk_count: int = 0
    projects_delayed_count: int = 0
    completed_this_week: int = 0
    team_member_count: int = 0


class PeriodProjectItem(BaseModel):
    project_id: str
    project_name: str
    location: str | None = None
    attendance_person_days: int = 0
    spend_credits_in_range: float = 0
    spend_debits_in_range: float = 0


class PeriodSummaryResponse(BaseModel):
    from_date: str
    to_date: str
    projects: list[PeriodProjectItem]
    total_attendance_person_days: int = 0
    total_spend_credits: float = 0
    total_spend_debits: float = 0


class LabourTrendDataPoint(BaseModel):
    """Single data point in labour payment trend analysis."""

    date: str  # YYYY-MM-DD
    total_payment: float
    worker_count: int


class LabourTrendsResponse(BaseModel):
    """Labour payment trends over a specified period."""

    period_days: int
    data: list[LabourTrendDataPoint]


class MaterialAlertItem(BaseModel):
    """Material stock alert when balance falls below threshold."""

    project_id: str
    project_name: str
    material_id: str
    material_name: str
    current_balance: float
    unit: str
    threshold: float
    alert_level: AlertLevel


class MaterialAlertsResponse(BaseModel):
    """Material stock alerts response with summary metadata."""

    alerts: list[MaterialAlertItem]
    total_alerts: int
