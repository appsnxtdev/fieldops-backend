from pydantic import BaseModel


class ProjectSummaryItem(BaseModel):
    project_id: str
    project_name: str
    location: str | None = None
    wallet_balance: float = 0
    task_count: int = 0
    due_tasks: int = 0
    today_attendance_count: int = 0


class DashboardSummaryResponse(BaseModel):
    projects: list[ProjectSummaryItem]
    total_sites: int = 0
    total_today_present: int = 0
    total_wallet_balance: float = 0
    total_tasks: int = 0
    total_due_tasks: int = 0
