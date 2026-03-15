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
