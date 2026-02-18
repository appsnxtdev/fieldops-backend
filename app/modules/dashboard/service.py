from datetime import date, datetime, timezone

from supabase import Client

from app.core.constants import DONE_TASK_STATUS_NAMES
from app.modules.attendance.service import list_attendance
from app.modules.dashboard.schemas import DashboardSummaryResponse, ProjectSummaryItem
from app.modules.expense.service import get_balance
from app.modules.projects.service import list_projects
from app.modules.tasks.schemas import TaskResponse
from app.modules.tasks.service import list_statuses, list_tasks


def _today_iso() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}-{now.day:02d}"


def _parse_due_date(due_at: str) -> date | None:
    if not due_at or not due_at.strip():
        return None
    s = due_at.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        pass
    if len(s) >= 10:
        try:
            return datetime.fromisoformat(s[:10]).date()
        except (ValueError, TypeError):
            pass
    return None


def _count_due_tasks(
    tasks: list[TaskResponse],
    status_id_to_name: dict[str, str],
    *,
    user_id: str | None = None,
    only_assigned_to_user: bool = False,
) -> int:
    today = datetime.now(timezone.utc).date()
    count = 0
    for t in tasks:
        if only_assigned_to_user and user_id and t.assignee_id != user_id:
            continue
        if not t.due_at:
            continue
        due_date = _parse_due_date(t.due_at)
        if due_date is None or due_date > today:
            continue
        status_name = (status_id_to_name.get(t.status_id or "") or "").strip()
        if status_name.upper() in {n.upper() for n in DONE_TASK_STATUS_NAMES}:
            continue
        count += 1
    return count


def get_dashboard_summary(
    supabase: Client,
    tenant_id: str,
    user_id: str,
    tenant_role: str | None,
) -> DashboardSummaryResponse:
    projects = list_projects(supabase, tenant_id, user_id, tenant_role=tenant_role)
    today = _today_iso()
    items: list[ProjectSummaryItem] = []
    total_present = 0
    total_wallet = 0.0
    total_tasks_count = 0
    total_due_count = 0
    only_my_tasks = tenant_role != "org_admin"
    for p in projects:
        balance = get_balance(supabase, p.id)
        tasks = list_tasks(supabase, p.id)
        statuses = list_statuses(supabase, p.id)
        status_id_to_name = {s.id: s.name for s in statuses}
        due_count = _count_due_tasks(
            tasks,
            status_id_to_name,
            user_id=user_id,
            only_assigned_to_user=only_my_tasks,
        )
        tasks_for_count = [t for t in tasks if not only_my_tasks or t.assignee_id == user_id] if only_my_tasks else tasks
        attendance = list_attendance(supabase, p.id, today)
        count_present = len(attendance)
        items.append(
            ProjectSummaryItem(
                project_id=p.id,
                project_name=p.name,
                location=p.location or p.address,
                wallet_balance=balance,
                task_count=len(tasks_for_count),
                due_tasks=due_count,
                today_attendance_count=count_present,
            )
        )
        total_present += count_present
        total_wallet += balance
        total_tasks_count += len(tasks_for_count)
        total_due_count += due_count
    return DashboardSummaryResponse(
        projects=items,
        total_sites=len(items),
        total_today_present=total_present,
        total_wallet_balance=round(total_wallet, 2),
        total_tasks=total_tasks_count,
        total_due_tasks=total_due_count,
    )
