"""Project health calculation logic.

This module provides date-based progress tracking to determine if a project
is on track, at risk, or delayed.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.modules.projects.constants import ProjectHealth


def calculate_project_health(
    start_date: date,
    end_date: date,
    total_tasks: int,
    completed_tasks: int,
    status: str = "active",
) -> Optional[ProjectHealth]:
    """Calculate project health based on timeline vs task completion progress.

    Algorithm:
    - If status is archived/completed → return None (health not applicable)
    - If no tasks exist → return "on_track" (new project, no issues yet)
    - If all tasks completed → return "on_track" (completed successfully)
    - If end_date has passed → "delayed"
    - Calculate time_progress (how much time has elapsed) and task_progress
    - If ≥80% time elapsed but <60% tasks done → "at_risk"
    - If ≥50% time elapsed but <30% tasks done → "delayed"
    - Otherwise → "on_track"

    Args:
        start_date: Project start date
        end_date: Project end date
        total_tasks: Total number of tasks in project
        completed_tasks: Number of completed tasks
        status: Project workflow status (planning/active/on_hold/completed/archived)

    Returns:
        ProjectHealth ("on_track", "at_risk", "delayed") or None if not applicable
    """
    # Don't calculate health for archived/completed projects
    if status in ("archived", "completed"):
        return None

    # If no tasks, assume on_track (new project)
    if total_tasks == 0:
        return "on_track"

    # If all tasks completed, project is on_track
    if completed_tasks >= total_tasks:
        return "on_track"

    # Check if project is past its deadline
    today = date.today()
    if today > end_date:
        return "delayed"

    # Calculate time progress (percentage of time elapsed)
    total_days = (end_date - start_date).days
    if total_days <= 0:
        # Edge case: same-day or invalid date range, assume on_track
        return "on_track"

    elapsed_days = (today - start_date).days
    time_progress = elapsed_days / total_days

    # Calculate task progress (percentage of tasks completed)
    task_progress = completed_tasks / total_tasks

    # Apply health rules
    # Rule 1: 80%+ time elapsed but <60% tasks done → at_risk
    if time_progress >= 0.80 and task_progress < 0.60:
        return "at_risk"

    # Rule 2: 50%+ time elapsed but <30% tasks done → delayed
    if time_progress >= 0.50 and task_progress < 0.30:
        return "delayed"

    # Rule 3: Otherwise on_track
    return "on_track"


def is_project_out_of_date(
    end_date: date,
    last_activity_at: Optional[datetime],
    status: str,
) -> bool:
    """Determine if a project is out of date.

    A project is out of date if:
    - End date has passed (unless status is "completed")
    - No activity for 30+ days (unless status is "completed")

    Args:
        end_date: Project end date
        last_activity_at: Last activity timestamp (or None)
        status: Project status (e.g., "active", "completed")

    Returns:
        True if project is out of date, False otherwise
    """
    # Completed projects are never out of date
    if status == "completed":
        return False

    today = date.today()

    # Check if end date has passed
    if end_date is not None and today > end_date:
        return True

    # Check if no activity for 30+ days
    if last_activity_at is not None:
        days_since_activity = (datetime.now(timezone.utc) - last_activity_at).days
        if days_since_activity >= 30:
            return True

    return False
