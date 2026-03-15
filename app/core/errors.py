"""
Shared error response shape and user-facing messages for API consumers.
Response JSON: { "detail": "<legacy>", "message": "<user-facing>", "code": "<optional>" }
"""

# User-facing messages for HTTP status codes (fallback when no code match)
DEFAULT_MESSAGES = {
    400: "The request was invalid. Please check your input and try again.",
    401: "Your session has expired or the link is invalid. Please sign in again.",
    403: "You don't have permission to do this.",
    404: "The requested item was not found.",
    422: "Please fix the highlighted fields and try again.",
    500: "Something went wrong. Please try again.",
    503: "Service temporarily unavailable. Please try again in a moment.",
}

# Map backend error text or code -> (user_message, code)
ATTENDANCE_MESSAGE_MAP = {
    "Outside allowed radius (500m from project location)": (
        "You must be at the site to check in.",
        "CHECK_IN_OUTSIDE_RADIUS",
    ),
    "Already checked in": (
        "You have already checked in for this date.",
        "ALREADY_CHECKED_IN",
    ),
    "No check-in found": (
        "No check-in was found for this date. Please check in first.",
        "NO_CHECK_IN_FOUND",
    ),
    "Must check in first": (
        "Please check in before checking out.",
        "MUST_CHECK_IN_FIRST",
    ),
    "Already checked out": (
        "You have already checked out for this date.",
        "ALREADY_CHECKED_OUT",
    ),
    "Failed to create attendance record": (
        "We couldn't save your attendance. Please try again.",
        "ATTENDANCE_CREATE_FAILED",
    ),
    "Failed to update attendance": (
        "We couldn't update your attendance. Please try again.",
        "ATTENDANCE_UPDATE_FAILED",
    ),
    "Photo file is empty": (
        "Please upload a valid photo.",
        "PHOTO_EMPTY",
    ),
}

PROJECT_MESSAGE_MAP = {
    "Project not found": ("This site could not be found.", "PROJECT_NOT_FOUND"),
    "Project not in your tenant": ("You don't have access to this site.", "PROJECT_NOT_IN_TENANT"),
    "Not a project member": ("You are not a member of this site.", "NOT_PROJECT_MEMBER"),
    "Insufficient permission": ("You don't have permission for this action.", "INSUFFICIENT_PERMISSION"),
}

AUTH_MESSAGE_MAP = {
    "Missing or invalid authorization header": (
        "Please sign in again.",
        "MISSING_AUTH_HEADER",
    ),
    "Missing token": ("Please sign in again.", "MISSING_TOKEN"),
    "Invalid token": ("Your session has expired. Please sign in again.", "INVALID_TOKEN"),
    "Missing tenant_id in token": (
        "Your account is not linked to an organization. Please contact support.",
        "MISSING_TENANT_ID",
    ),
    "Tenant org_admin required": (
        "Only organization admins can do this.",
        "ORG_ADMIN_REQUIRED",
    ),
}

GENERIC_MESSAGE_MAP = {
    "Task not found": ("This task was not found.", "TASK_NOT_FOUND"),
    "Report not found": ("This report was not found.", "REPORT_NOT_FOUND"),
    "Material not found": ("This material was not found.", "MATERIAL_NOT_FOUND"),
    "Master material not found": ("This material type was not found.", "MASTER_MATERIAL_NOT_FOUND"),
    "Object not found": ("The requested file was not found.", "OBJECT_NOT_FOUND"),
    "Database unavailable": ("Service temporarily unavailable. Please try again.", "DATABASE_UNAVAILABLE"),
    "Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)": (
        "Service is not configured. Please contact support.",
        "SERVICE_NOT_CONFIGURED",
    ),
}


def get_user_message(detail: str | None, status_code: int) -> tuple[str, str | None]:
    """
    Return (user_message, code) for a given detail string and status code.
    detail can be the raw exception message or HTTPException detail.
    """
    if not detail:
        return (DEFAULT_MESSAGES.get(status_code, DEFAULT_MESSAGES[500]), None)
    detail_str = str(detail).strip()
    for mapping in (
        ATTENDANCE_MESSAGE_MAP,
        PROJECT_MESSAGE_MAP,
        AUTH_MESSAGE_MAP,
        GENERIC_MESSAGE_MAP,
    ):
        for key, (msg, code) in mapping.items():
            if key in detail_str or detail_str == key:
                return (msg, code)
    # If detail looks user-safe and short, use it; else generic
    if len(detail_str) < 120 and "\n" not in detail_str:
        return (detail_str, None)
    return (DEFAULT_MESSAGES.get(status_code, DEFAULT_MESSAGES[500]), None)
