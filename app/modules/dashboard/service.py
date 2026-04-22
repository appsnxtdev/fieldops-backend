from datetime import date, datetime, timedelta, timezone

from supabase import Client

from app.core.constants import DONE_TASK_STATUS_NAMES, MATERIAL_LOW_STOCK_THRESHOLD
from app.modules.attendance.service import list_attendance, list_attendance_in_range
from app.modules.dashboard.schemas import (
    ComparisonSnapshot,
    DashboardSummaryResponse,
    LabourTrendDataPoint,
    LabourTrendsResponse,
    MaterialAlertItem,
    MaterialAlertsResponse,
    PeriodProjectItem,
    PeriodSummaryResponse,
    ProjectSummaryItem,
)
from app.modules.expense.service import get_balance, list_transactions as list_expense_transactions
from app.modules.labour.service import list_labour_in_range
from app.modules.materials.service import list_materials_with_balance
from app.modules.projects.health import calculate_project_health, is_project_out_of_date
from app.modules.projects.service import get_project_members, get_user_admin_projects, list_projects
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


def _count_completed_tasks(tasks: list[TaskResponse], statuses: list) -> int:
    """Count tasks in 'done' status."""
    done_status_names = {n.upper() for n in DONE_TASK_STATUS_NAMES}
    status_id_to_name = {s.id: s.name for s in statuses}
    return sum(
        1 for t in tasks
        if status_id_to_name.get(t.status_id, "").upper() in done_status_names
    )


def _count_due_tasks(
    tasks: list[TaskResponse],
    status_id_to_name: dict[str, str],
) -> int:
    """Count tasks that are due (due date <= today and not completed)."""
    today = datetime.now(timezone.utc).date()
    count = 0
    for t in tasks:
        # Filtering is done before calling this function
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


def _calculate_project_health(
    tasks: list[TaskResponse],
    statuses: list,
    start_date: date | None = None,
    end_date: date | None = None,
    workflow_status: str | None = None,
) -> str | None:
    """
    Calculate project health using health.py logic.
    Returns None only for archived/completed projects.
    For projects without dates, uses simple task-based fallback.
    """
    # Don't calculate health for archived/completed projects
    if workflow_status in ("archived", "completed"):
        return None

    # Use health.py calculation if we have dates
    if start_date and end_date:
        total_tasks = len(tasks)
        completed_tasks = _count_completed_tasks(tasks, statuses)

        health = calculate_project_health(
            start_date=start_date,
            end_date=end_date,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            status=workflow_status or "planning",
        )

        return health

    # Fallback: simple task-based health for projects without dates
    total_tasks = len(tasks)
    if total_tasks == 0:
        return "on_track"  # New project, no tasks yet

    completed_tasks = _count_completed_tasks(tasks, statuses)
    completion_pct = (completed_tasks / total_tasks) * 100

    # Simple thresholds for projects without timeline
    if completion_pct >= 70:
        return "on_track"
    elif completion_pct >= 40:
        return "at_risk"
    else:
        return "delayed"


def _calculate_task_completion_percentage(
    tasks: list[TaskResponse],
    statuses: list,
) -> float:
    """Calculate percentage of tasks completed"""
    if not tasks:
        return 0.0

    completed_count = _count_completed_tasks(tasks, statuses)
    return round((completed_count / len(tasks)) * 100, 1)


def _count_completed_this_week(
    tasks: list[TaskResponse],
    statuses: list,
) -> int:
    """Count tasks completed in last 7 days."""
    done_status_names = {n.upper() for n in DONE_TASK_STATUS_NAMES}
    status_id_to_name = {s.id: s.name for s in statuses}

    today = datetime.now(timezone.utc).date()
    seven_days_ago = today - timedelta(days=7)

    count = 0
    for t in tasks:
        # Check if task is in done status
        status_name = status_id_to_name.get(t.status_id, "").upper()
        if status_name not in done_status_names:
            continue

        # Check if updated within last 7 days
        if not t.updated_at:
            continue

        try:
            updated_date = datetime.fromisoformat(
                t.updated_at.replace("Z", "+00:00")
            ).date()
            if updated_date >= seven_days_ago:
                count += 1
        except (ValueError, AttributeError):
            pass

    return count


def _get_member_projects_with_tasks(
    supabase: Client,
    tenant_id: str,
    user_id: str,
    all_projects: list,
) -> tuple[list, list[TaskResponse], dict]:
    """
    Get projects where member has assigned tasks.

    Returns:
        tuple: (filtered_projects, all_user_tasks, tasks_by_project_id)
    """
    user_tasks = []
    tasks_by_project = {}  # Cache tasks to avoid re-fetching

    for proj in all_projects:
        tasks = list_tasks(supabase, proj.id)
        tasks_by_project[proj.id] = tasks  # Store for reuse
        user_proj_tasks = [t for t in tasks if t.assignee_id == user_id]
        user_tasks.extend(user_proj_tasks)

    # Filter to projects where user has tasks
    project_ids_with_tasks = {t.project_id for t in user_tasks}
    filtered_projects = [p for p in all_projects if p.id in project_ids_with_tasks]

    return filtered_projects, user_tasks, tasks_by_project


def _get_snapshot_for_date(
    supabase: Client,
    tenant_id: str,
    user_id: str,
    tenant_role: str | None,
    target_date: str,
) -> ComparisonSnapshot:
    """Calculate dashboard metrics snapshot for a specific date."""
    projects = list_projects(supabase, tenant_id, user_id, tenant_role=tenant_role)

    total_sites = len(projects)
    total_wallet = 0.0
    total_tasks_count = 0
    total_present = 0

    for p in projects:
        # Wallet balance at target date
        balance = get_balance(supabase, p.id)
        total_wallet += balance

        # Tasks count (role-filtered if needed)
        tasks = list_tasks(supabase, p.id)
        if tenant_role == "member":
            tasks_for_count = [t for t in tasks if t.assignee_id == user_id]
        else:
            tasks_for_count = tasks
        total_tasks_count += len(tasks_for_count)

        # Attendance for target date
        attendance = list_attendance(supabase, p.id, target_date)
        total_present += len(attendance)

    return ComparisonSnapshot(
        total_sites=total_sites,
        total_wallet_balance=round(total_wallet, 2),
        total_tasks=total_tasks_count,
        total_today_present=total_present,
    )


def get_dashboard_summary(
    supabase: Client,
    tenant_id: str,
    user_id: str,
    tenant_role: str | None,
) -> DashboardSummaryResponse:
    projects = list_projects(supabase, tenant_id, user_id, tenant_role=tenant_role)
    today = _today_iso()

    # Check if user is project admin (after org_admin, before member)
    is_project_admin = False
    admin_projects = []
    if tenant_role != "org_admin":
        admin_projects = get_user_admin_projects(supabase, tenant_id, user_id)
        if admin_projects:
            is_project_admin = True
            projects = admin_projects

    # For members, filter to only projects where they have tasks
    all_user_tasks = []  # Will store all user's tasks if member role
    tasks_cache = {}  # Cache tasks to avoid redundant queries
    if tenant_role == "member" and not is_project_admin:
        projects, all_user_tasks, tasks_cache = _get_member_projects_with_tasks(
            supabase, tenant_id, user_id, projects
        )

    items: list[ProjectSummaryItem] = []
    total_present = 0
    total_wallet = 0.0
    total_tasks_count = 0
    total_due_count = 0
    # Health distribution counters
    on_track_count = 0
    at_risk_count = 0
    delayed_count = 0
    project_statuses_map = {}  # Cache statuses to avoid redundant queries
    for p in projects:
        balance = get_balance(supabase, p.id)
        rounded_balance = round(balance, 2)
        # Reuse cached tasks for members to avoid redundant queries
        if tenant_role == "member" and not is_project_admin:
            tasks = tasks_cache.get(p.id, [])
        else:
            tasks = list_tasks(supabase, p.id)

        # For members, filter to only their tasks for this project
        if tenant_role == "member" and not is_project_admin:
            tasks_for_project = [t for t in all_user_tasks if t.project_id == p.id]
        else:
            tasks_for_project = tasks

        statuses = list_statuses(supabase, p.id)
        project_statuses_map[p.id] = statuses  # Cache for reuse in member metrics
        status_id_to_name = {s.id: s.name for s in statuses}
        # tasks_for_project already filtered for members, no need for only_assigned_to_user
        due_count = _count_due_tasks(
            tasks_for_project,
            status_id_to_name,
        )
        tasks_for_count = tasks_for_project  # Already filtered above
        attendance = list_attendance(supabase, p.id, today)
        count_present = len(attendance)

        # Calculate completion percentage
        completion_pct = _calculate_task_completion_percentage(tasks_for_count, statuses)

        # Get workflow status (defaults to 'planning' if not set)
        workflow_status = p.status or "planning"

        # Calculate project health using health.py with lifecycle dates
        project_health = _calculate_project_health(
            tasks,  # Project health is based on ALL tasks, not role-filtered
            statuses,
            start_date=p.start_date,
            end_date=p.end_date,
            workflow_status=workflow_status,
        )

        # Count material alerts for this project
        materials = list_materials_with_balance(supabase, p.id)
        material_alerts_count = sum(
            1 for m in materials if m.balance < MATERIAL_LOW_STOCK_THRESHOLD
        )

        # Determine if project is out of date
        out_of_date = False
        last_activity_at_str = None
        if p.end_date or p.last_activity_at:
            # Parse last_activity_at from project field or fall back to updated_at
            last_activity = None
            if p.last_activity_at:
                try:
                    last_activity = datetime.fromisoformat(p.last_activity_at.replace("Z", "+00:00"))
                    last_activity_at_str = p.last_activity_at
                except (ValueError, AttributeError):
                    pass
            elif p.updated_at:
                try:
                    last_activity = datetime.fromisoformat(p.updated_at.replace("Z", "+00:00"))
                    last_activity_at_str = p.updated_at
                except (ValueError, AttributeError):
                    pass

            out_of_date = is_project_out_of_date(
                end_date=p.end_date,
                last_activity_at=last_activity,
                status=workflow_status,
            )

        # Get project admin info
        project_admin_name = None
        if p.project_admin_user_id:
            # Try to fetch admin user info from profiles
            try:
                from app.core.constants import DB_SCHEMA
                admin_result = (
                    supabase.schema(DB_SCHEMA)
                    .table("profiles")
                    .select("full_name")
                    .eq("id", p.project_admin_user_id)
                    .limit(1)
                    .execute()
                )
                if admin_result.data:
                    project_admin_name = admin_result.data[0].get("full_name")
            except Exception:
                pass  # Gracefully handle any errors fetching admin info

        # Track health distribution
        if project_health == "on_track":
            on_track_count += 1
        elif project_health == "at_risk":
            at_risk_count += 1
        elif project_health == "delayed":
            delayed_count += 1

        items.append(
            ProjectSummaryItem(
                project_id=p.id,
                project_name=p.name,
                location=p.location or p.address,
                lat=p.lat,
                lng=p.lng,
                wallet_balance=0.0 if (tenant_role == "member" and not is_project_admin) else rounded_balance,
                task_count=len(tasks_for_count),
                due_tasks=due_count,
                today_attendance_count=0 if (tenant_role == "member" and not is_project_admin) else count_present,
                workflow_status=workflow_status,
                health=project_health,
                task_completion_percentage=completion_pct,
                material_alerts=0 if (tenant_role == "member" and not is_project_admin) else material_alerts_count,
                is_out_of_date=out_of_date,
                last_activity_at=last_activity_at_str,
                project_admin_user_id=p.project_admin_user_id,
                project_admin_name=project_admin_name,
            )
        )
        # Only aggregate visible metrics for members (but show for project admins)
        total_present += count_present if (tenant_role != "member" or is_project_admin) else 0
        total_wallet += rounded_balance if (tenant_role != "member" or is_project_admin) else 0
        total_tasks_count += len(tasks_for_count)
        total_due_count += due_count

    # Calculate completed_this_week for members
    completed_this_week = 0
    if tenant_role == "member" and not is_project_admin and all_user_tasks:
        # Reuse already-fetched statuses from main loop
        all_statuses = []
        for p in projects:
            all_statuses.extend(project_statuses_map[p.id])

        completed_this_week = _count_completed_this_week(all_user_tasks, all_statuses)

    # For members (not project admins), set snapshots to None
    if tenant_role == "member" and not is_project_admin:
        yesterday_snapshot = None
        last_week_snapshot = None
        last_month_snapshot = None
    else:
        # Calculate snapshots for org_admin and project_admin
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        last_week = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        last_month = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        yesterday_snapshot = _get_snapshot_for_date(supabase, tenant_id, user_id, tenant_role, yesterday)
        last_week_snapshot = _get_snapshot_for_date(supabase, tenant_id, user_id, tenant_role, last_week)
        last_month_snapshot = _get_snapshot_for_date(supabase, tenant_id, user_id, tenant_role, last_month)

    # Get material alerts (skip for regular members, but include for project admins)
    material_alerts_total = 0
    if tenant_role != "member" or is_project_admin:
        material_alerts_result = get_material_alerts(supabase, tenant_id, user_id, tenant_role=tenant_role)
        material_alerts_total = material_alerts_result.total_alerts

    # Calculate team_member_count for project admins
    team_member_count = 0
    if is_project_admin:
        # Get unique members across all admin projects
        unique_members = set()
        for p in admin_projects:
            members = get_project_members(supabase, p.id)
            for member in members:
                unique_members.add(member.user_id)
        team_member_count = len(unique_members)

    return DashboardSummaryResponse(
        projects=items,
        total_sites=len(items),
        total_today_present=total_present,
        total_wallet_balance=round(total_wallet, 2),
        total_tasks=total_tasks_count,
        total_due_tasks=total_due_count,
        yesterday_snapshot=yesterday_snapshot,
        last_week_snapshot=last_week_snapshot,
        last_month_snapshot=last_month_snapshot,
        material_alerts_count=material_alerts_total,
        projects_on_track_count=on_track_count,
        projects_at_risk_count=at_risk_count,
        projects_delayed_count=delayed_count,
        completed_this_week=completed_this_week,
        team_member_count=team_member_count,
    )


def get_period_summary(
    supabase: Client,
    tenant_id: str,
    user_id: str,
    tenant_role: str | None,
    from_date: str,
    to_date: str,
) -> PeriodSummaryResponse:
    projects = list_projects(supabase, tenant_id, user_id, tenant_role=tenant_role)
    items: list[PeriodProjectItem] = []
    total_attendance = 0
    total_credits = 0.0
    total_debits = 0.0
    for p in projects:
        attendance_rows = list_attendance_in_range(supabase, p.id, from_date, to_date)
        person_days = len(attendance_rows)
        transactions = list_expense_transactions(supabase, p.id)
        credits = 0.0
        debits = 0.0
        for t in transactions:
            if not t.created_at:
                continue
            day = t.created_at[:10] if len(t.created_at) >= 10 else t.created_at
            if from_date <= day <= to_date:
                if t.type == "credit": credits += t.amount
                else: debits += t.amount
        items.append(PeriodProjectItem(
            project_id=p.id, project_name=p.name, location=p.location or p.address,
            attendance_person_days=person_days, spend_credits_in_range=round(credits, 2), spend_debits_in_range=round(debits, 2),
        ))
        total_attendance += person_days
        total_credits += credits
        total_debits += debits
    return PeriodSummaryResponse(from_date=from_date, to_date=to_date, projects=items,
        total_attendance_person_days=total_attendance, total_spend_credits=round(total_credits, 2), total_spend_debits=round(total_debits, 2),
    )


def get_labour_trends(
    supabase: Client,
    tenant_id: str,
    user_id: str,
    tenant_role: str | None,
    period_days: int = 30,
) -> LabourTrendsResponse:
    """
    Calculate labour payment trends over the specified period.
    Groups labour daily records by date and aggregates total payment and worker count.
    Applies role-based filtering to only include projects the user has access to.

    Args:
        supabase: Supabase client
        tenant_id: Tenant ID
        user_id: User ID
        tenant_role: User's role in tenant (org_admin, member, etc.)
        period_days: Number of days to look back (default 30)

    Returns:
        LabourTrendsResponse with data points sorted chronologically
    """
    # Get accessible projects for role-based filtering
    projects = list_projects(supabase, tenant_id, user_id, tenant_role=tenant_role)
    if not projects:
        return LabourTrendsResponse(period_days=period_days, data=[])

    # Calculate date range
    today_dt = datetime.now(timezone.utc)
    from_date = (today_dt - timedelta(days=period_days - 1)).strftime("%Y-%m-%d")
    to_date = today_dt.strftime("%Y-%m-%d")

    # Collect all labour records across accessible projects
    all_labour_records = []
    for project in projects:
        records = list_labour_in_range(supabase, project.id, from_date, to_date)
        all_labour_records.extend(records)

    # Group by date and aggregate
    date_aggregates: dict[str, dict[str, float | int]] = {}
    for record in all_labour_records:
        record_date = record.get("date")
        if not record_date:
            continue

        # Convert date to string format if it's a date object
        if isinstance(record_date, date):
            date_str = record_date.strftime("%Y-%m-%d")
        else:
            date_str = str(record_date)

        count = record.get("count", 0)
        labour_type = record.get("labour_types", {})
        rate_per_day = float(labour_type.get("rate_per_day", 0)) if labour_type else 0.0

        payment = count * rate_per_day

        if date_str not in date_aggregates:
            date_aggregates[date_str] = {"total_payment": 0.0, "worker_count": 0}

        date_aggregates[date_str]["total_payment"] += payment
        date_aggregates[date_str]["worker_count"] += count

    # Build data points sorted by date
    data_points = [
        LabourTrendDataPoint(
            date=date_str,
            total_payment=round(agg["total_payment"], 2),
            worker_count=int(agg["worker_count"]),
        )
        for date_str, agg in date_aggregates.items()
    ]

    # Sort chronologically
    data_points.sort(key=lambda x: x.date)

    return LabourTrendsResponse(period_days=period_days, data=data_points)


def get_material_alerts(
    supabase: Client,
    tenant_id: str,
    user_id: str,
    tenant_role: str | None,
) -> MaterialAlertsResponse:
    """
    Get materials with low stock across all accessible projects.

    Identifies materials where current_balance < threshold (20.0 units by default).
    Applies role-based filtering to only include projects the user has access to.

    Args:
        supabase: Supabase client
        tenant_id: Tenant ID
        user_id: User ID
        tenant_role: User's role in tenant (org_admin, member, etc.)

    Returns:
        MaterialAlertsResponse with alert items and total count
    """
    # Get accessible projects for role-based filtering
    projects = list_projects(supabase, tenant_id, user_id, tenant_role=tenant_role)
    if not projects:
        return MaterialAlertsResponse(alerts=[], total_alerts=0)

    # Use threshold from constants
    THRESHOLD = MATERIAL_LOW_STOCK_THRESHOLD

    alerts: list[MaterialAlertItem] = []

    # Check materials for each accessible project
    for project in projects:
        materials = list_materials_with_balance(supabase, project.id)

        for material in materials:
            # Alert if current balance is below threshold
            if material.balance < THRESHOLD:
                alerts.append(
                    MaterialAlertItem(
                        project_id=project.id,
                        project_name=project.name,
                        material_id=material.id,
                        material_name=material.name,
                        current_balance=material.balance,
                        unit=material.unit,
                        threshold=THRESHOLD,
                        alert_level="low",
                    )
                )

    # Sort by severity (lowest balance first)
    alerts.sort(key=lambda x: x.current_balance)

    return MaterialAlertsResponse(alerts=alerts, total_alerts=len(alerts))
