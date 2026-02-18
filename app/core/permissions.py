"""Permission constants and role -> permissions map."""

CAN_MANAGE_PROJECT = "can_manage_project"
CAN_VIEW_PROJECT = "can_view_project"
CAN_MANAGE_TASKS = "can_manage_tasks"
CAN_MANAGE_TASK_STATUSES = "can_manage_task_statuses"
CAN_LOG_ATTENDANCE = "can_log_attendance"
CAN_VIEW_ATTENDANCE = "can_view_attendance"
CAN_MANAGE_DAILY_REPORTS = "can_manage_daily_reports"
CAN_VIEW_DAILY_REPORTS = "can_view_daily_reports"
CAN_MANAGE_MATERIALS = "can_manage_materials"
CAN_VIEW_MATERIALS = "can_view_materials"
CAN_MANAGE_EXPENSE = "can_manage_expense"
CAN_VIEW_EXPENSE = "can_view_expense"
CAN_MANAGE_MEMBERS = "can_manage_members"
"""Permission constants and role -> permissions map."""

CAN_MANAGE_PROJECT = "can_manage_project"
CAN_VIEW_PROJECT = "can_view_project"
CAN_MANAGE_TASKS = "can_manage_tasks"
CAN_MANAGE_TASK_STATUSES = "can_manage_task_statuses"
CAN_LOG_ATTENDANCE = "can_log_attendance"
CAN_VIEW_ATTENDANCE = "can_view_attendance"
CAN_MANAGE_DAILY_REPORTS = "can_manage_daily_reports"
CAN_VIEW_DAILY_REPORTS = "can_view_daily_reports"
CAN_MANAGE_MATERIALS = "can_manage_materials"
CAN_VIEW_MATERIALS = "can_view_materials"
CAN_MANAGE_EXPENSE = "can_manage_expense"
CAN_VIEW_EXPENSE = "can_view_expense"
CAN_MANAGE_MEMBERS = "can_manage_members"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [
        CAN_MANAGE_PROJECT,
        CAN_VIEW_PROJECT,
        CAN_MANAGE_TASKS,
        CAN_MANAGE_TASK_STATUSES,
        CAN_LOG_ATTENDANCE,
        CAN_VIEW_ATTENDANCE,
        CAN_MANAGE_DAILY_REPORTS,
        CAN_VIEW_DAILY_REPORTS,
        CAN_MANAGE_MATERIALS,
        CAN_VIEW_MATERIALS,
        CAN_MANAGE_EXPENSE,
        CAN_VIEW_EXPENSE,
        CAN_MANAGE_MEMBERS,
    ],
    "member": [
        CAN_VIEW_PROJECT,
        CAN_MANAGE_TASKS,
        CAN_LOG_ATTENDANCE,
        CAN_VIEW_ATTENDANCE,
        CAN_MANAGE_DAILY_REPORTS,
        CAN_VIEW_DAILY_REPORTS,
        CAN_MANAGE_MATERIALS,
        CAN_VIEW_MATERIALS,
        CAN_MANAGE_EXPENSE,
        CAN_VIEW_EXPENSE,
    ],
    "viewer": [
        CAN_VIEW_PROJECT,
        CAN_VIEW_ATTENDANCE,
        CAN_VIEW_DAILY_REPORTS,
        CAN_VIEW_MATERIALS,
        CAN_VIEW_EXPENSE,
    ],
}


def has_permission(role: str, permission: str) -> bool:
    return role in ROLE_PERMISSIONS and permission in ROLE_PERMISSIONS[role]
"""Permission constants and role -> permissions map."""

CAN_MANAGE_PROJECT = "can_manage_project"
CAN_VIEW_PROJECT = "can_view_project"
CAN_MANAGE_TASKS = "can_manage_tasks"
CAN_MANAGE_TASK_STATUSES = "can_manage_task_statuses"
CAN_LOG_ATTENDANCE = "can_log_attendance"
CAN_VIEW_ATTENDANCE = "can_view_attendance"
CAN_MANAGE_DAILY_REPORTS = "can_manage_daily_reports"
CAN_VIEW_DAILY_REPORTS = "can_view_daily_reports"
CAN_MANAGE_MATERIALS = "can_manage_materials"
CAN_VIEW_MATERIALS = "can_view_materials"
CAN_MANAGE_EXPENSE = "can_manage_expense"
CAN_VIEW_EXPENSE = "can_view_expense"
CAN_MANAGE_MEMBERS = "can_manage_members"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [
        CAN_MANAGE_PROJECT,
        CAN_VIEW_PROJECT,
        CAN_MANAGE_TASKS,
        CAN_MANAGE_TASK_STATUSES,
        CAN_LOG_ATTENDANCE,
        CAN_VIEW_ATTENDANCE,
        CAN_MANAGE_DAILY_REPORTS,
        CAN_VIEW_DAILY_REPORTS,
        CAN_MANAGE_MATERIALS,
        CAN_VIEW_MATERIALS,
        CAN_MANAGE_EXPENSE,
        CAN_VIEW_EXPENSE,
        CAN_MANAGE_MEMBERS,
    ],
    "member": [
        CAN_VIEW_PROJECT,
        CAN_MANAGE_TASKS,
        CAN_LOG_ATTENDANCE,
        CAN_VIEW_ATTENDANCE,
        CAN_MANAGE_DAILY_REPORTS,
        CAN_VIEW_DAILY_REPORTS,
        CAN_MANAGE_MATERIALS,
        CAN_VIEW_MATERIALS,
        CAN_MANAGE_EXPENSE,
        CAN_VIEW_EXPENSE,
    ],
    "viewer": [
        CAN_VIEW_PROJECT,
        CAN_VIEW_ATTENDANCE,
        CAN_VIEW_DAILY_REPORTS,
        CAN_VIEW_MATERIALS,
        CAN_VIEW_EXPENSE,
    ],
}


def has_permission(role: str, permission: str) -> bool:
    return role in ROLE_PERMISSIONS and permission in ROLE_PERMISSIONS[role]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [
        CAN_MANAGE_PROJECT,
        CAN_VIEW_PROJECT,
        CAN_MANAGE_TASKS,
        CAN_MANAGE_TASK_STATUSES,
        CAN_LOG_ATTENDANCE,
        CAN_VIEW_ATTENDANCE,
        CAN_MANAGE_DAILY_REPORTS,
        CAN_VIEW_DAILY_REPORTS,
        CAN_MANAGE_MATERIALS,
        CAN_VIEW_MATERIALS,
        CAN_MANAGE_EXPENSE,
        CAN_VIEW_EXPENSE,
        CAN_MANAGE_MEMBERS,
    ],
    "member": [
        CAN_VIEW_PROJECT,
        CAN_MANAGE_TASKS,
        CAN_LOG_ATTENDANCE,
        CAN_VIEW_ATTENDANCE,
        CAN_MANAGE_DAILY_REPORTS,
        CAN_VIEW_DAILY_REPORTS,
        CAN_MANAGE_MATERIALS,
        CAN_VIEW_MATERIALS,
        CAN_VIEW_EXPENSE,
    ],
    "viewer": [
        CAN_VIEW_PROJECT,
        CAN_VIEW_ATTENDANCE,
        CAN_VIEW_DAILY_REPORTS,
        CAN_VIEW_MATERIALS,
        CAN_VIEW_EXPENSE,
    ],
}


def has_permission(role: str, permission: str) -> bool:
    return role in ROLE_PERMISSIONS and permission in ROLE_PERMISSIONS[role]
