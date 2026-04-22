import pytest
from unittest.mock import Mock
from app.modules.dashboard.service import (
    _count_completed_tasks,
    _calculate_project_status,
    _calculate_task_completion_percentage,
)
from app.modules.tasks.schemas import TaskResponse


class MockStatus:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


def test_count_completed_tasks_returns_count_of_done_tasks():
    """Test that _count_completed_tasks correctly counts tasks in done status."""
    statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "In Progress"),
        MockStatus("status-3", "Done"),
        MockStatus("status-4", "Complete"),
    ]

    tasks = [
        TaskResponse(id="t1", title="Task 1", status_id="status-1", project_id="p1"),
        TaskResponse(id="t2", title="Task 2", status_id="status-3", project_id="p1"),
        TaskResponse(id="t3", title="Task 3", status_id="status-2", project_id="p1"),
        TaskResponse(id="t4", title="Task 4", status_id="status-4", project_id="p1"),
        TaskResponse(id="t5", title="Task 5", status_id="status-3", project_id="p1"),
    ]

    count = _count_completed_tasks(tasks, statuses)
    assert count == 3  # 2 Done + 1 Complete


def test_count_completed_tasks_empty_list():
    """Test that _count_completed_tasks handles empty task list."""
    statuses = [MockStatus("status-1", "Done")]
    tasks = []

    count = _count_completed_tasks(tasks, statuses)
    assert count == 0


def test_calculate_task_completion_percentage_uses_helper():
    """Test that _calculate_task_completion_percentage uses the helper function."""
    statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    tasks = [
        TaskResponse(id="t1", title="Task 1", status_id="status-1", project_id="p1"),
        TaskResponse(id="t2", title="Task 2", status_id="status-2", project_id="p1"),
        TaskResponse(id="t3", title="Task 3", status_id="status-2", project_id="p1"),
        TaskResponse(id="t4", title="Task 4", status_id="status-1", project_id="p1"),
    ]

    pct = _calculate_task_completion_percentage(tasks, statuses)
    assert pct == 50.0  # 2 out of 4 = 50%


def test_calculate_project_status_uses_helper():
    """Test that _calculate_project_status uses the helper function."""
    from datetime import date
    statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    tasks = [
        TaskResponse(id="t1", title="Task 1", status_id="status-1", project_id="p1"),
        TaskResponse(id="t2", title="Task 2", status_id="status-2", project_id="p1"),
        TaskResponse(id="t3", title="Task 3", status_id="status-2", project_id="p1"),
        TaskResponse(id="t4", title="Task 4", status_id="status-2", project_id="p1"),
        TaskResponse(id="t5", title="Task 5", status_id="status-2", project_id="p1"),
    ]

    # 4 out of 5 = 80% (should be on_track) - fallback logic without dates
    status = _calculate_project_status(tasks, statuses, start_date=None, end_date=None)
    assert status == "on_track"


def test_project_status_calculation_independent_of_role_filtering():
    """
    CRITICAL TEST: Verify that project status is calculated from ALL tasks,
    not role-filtered tasks. This ensures project health is a project attribute,
    not a user attribute.
    """
    statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    # All project tasks (10 tasks, 8 done = 80% - should be on_track)
    all_tasks = [
        TaskResponse(id="t1", title="Task 1", status_id="status-2", project_id="p1", assignee_id="user-1"),
        TaskResponse(id="t2", title="Task 2", status_id="status-2", project_id="p1", assignee_id="user-1"),
        TaskResponse(id="t3", title="Task 3", status_id="status-2", project_id="p1", assignee_id="user-2"),
        TaskResponse(id="t4", title="Task 4", status_id="status-2", project_id="p1", assignee_id="user-2"),
        TaskResponse(id="t5", title="Task 5", status_id="status-2", project_id="p1", assignee_id="user-2"),
        TaskResponse(id="t6", title="Task 6", status_id="status-2", project_id="p1", assignee_id="user-2"),
        TaskResponse(id="t7", title="Task 7", status_id="status-2", project_id="p1", assignee_id="user-2"),
        TaskResponse(id="t8", title="Task 8", status_id="status-2", project_id="p1", assignee_id="user-2"),
        TaskResponse(id="t9", title="Task 9", status_id="status-1", project_id="p1", assignee_id="user-1"),
        TaskResponse(id="t10", title="Task 10", status_id="status-1", project_id="p1", assignee_id="user-2"),
    ]

    # User 1's tasks only (2 done out of 3 = 66% - would be at_risk if we used this)
    user1_tasks = [t for t in all_tasks if t.assignee_id == "user-1"]

    # Project status should be based on ALL tasks (80% completion = on_track) - fallback logic
    project_status = _calculate_project_status(all_tasks, statuses, start_date=None, end_date=None)
    assert project_status == "on_track"

    # User completion percentage CAN be role-filtered (66%)
    user_completion_pct = _calculate_task_completion_percentage(user1_tasks, statuses)
    assert user_completion_pct == 66.7

    # But if we wrongly used user1_tasks for project status, it would be at_risk
    wrong_project_status = _calculate_project_status(user1_tasks, statuses, start_date=None, end_date=None)
    assert wrong_project_status == "at_risk"  # This proves the bug would happen

    # The fix ensures we use all_tasks for project status, not user1_tasks


def test_project_status_thresholds():
    """Test project status threshold logic for fallback calculation."""
    statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    # 70%+ = on_track (fallback logic without dates)
    tasks_70 = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="p1") for i in range(7)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="p1") for i in range(7, 10)],
    ]
    assert _calculate_project_status(tasks_70, statuses, start_date=None, end_date=None) == "on_track"

    # 40-69% = at_risk (fallback logic)
    tasks_50 = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="p1") for i in range(5)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="p1") for i in range(5, 10)],
    ]
    assert _calculate_project_status(tasks_50, statuses, start_date=None, end_date=None) == "at_risk"

    # <40% = delayed (fallback logic)
    tasks_30 = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="p1") for i in range(3)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="p1") for i in range(3, 10)],
    ]
    assert _calculate_project_status(tasks_30, statuses, start_date=None, end_date=None) == "delayed"


def test_get_snapshot_for_date_calculates_metrics_correctly():
    """Test snapshot calculation for a specific date."""
    from datetime import datetime, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import _get_snapshot_for_date
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.attendance.schemas import AttendanceResponse

    target_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # Mock Supabase client
    mock_supabase = Mock()

    # Mock projects
    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
        ProjectResponse(id="proj-2", tenant_id="tenant-1", name="Site B", timezone="Asia/Kolkata", address="Location B"),
    ]

    # Mock tasks for projects
    mock_tasks_proj1 = [
        TaskResponse(id=f"t{i}", title=f"Task {i}", project_id="proj-1", assignee_id="user-1")
        for i in range(8)
    ]
    mock_tasks_proj2 = [
        TaskResponse(id=f"t{i}", title=f"Task {i}", project_id="proj-2", assignee_id="user-1")
        for i in range(7)
    ]

    # Mock attendance
    mock_attendance_proj1 = [
        Mock(id=f"att{i}", worker_id=f"worker-{i}", date=target_date)
        for i in range(5)
    ]
    mock_attendance_proj2 = [
        Mock(id=f"att{i}", worker_id=f"worker-{i}", date=target_date)
        for i in range(3)
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", side_effect=[800.0, 700.0]), \
         patch("app.modules.dashboard.service.list_tasks", side_effect=[mock_tasks_proj1, mock_tasks_proj2]), \
         patch("app.modules.dashboard.service.list_attendance", side_effect=[mock_attendance_proj1, mock_attendance_proj2]):

        snapshot = _get_snapshot_for_date(mock_supabase, "tenant-1", "user-1", "org_admin", target_date)

        assert snapshot.total_sites == 2
        assert snapshot.total_wallet_balance == 1500.0
        assert snapshot.total_tasks == 15
        assert snapshot.total_today_present == 8


def test_get_snapshot_for_date_with_role_filtering():
    """Test snapshot calculation respects role-based filtering for regular members."""
    from datetime import datetime, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import _get_snapshot_for_date
    from app.modules.projects.schemas import ProjectResponse

    target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # Tasks: 5 assigned to user-1, 3 assigned to user-2
    mock_tasks = [
        TaskResponse(id=f"t{i}", title=f"Task {i}", project_id="proj-1", assignee_id="user-1")
        for i in range(5)
    ] + [
        TaskResponse(id=f"t{i}", title=f"Task {i}", project_id="proj-1", assignee_id="user-2")
        for i in range(5, 8)
    ]

    mock_attendance = [Mock(id=f"att{i}", worker_id=f"worker-{i}", date=target_date) for i in range(3)]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=1000.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_attendance", return_value=mock_attendance):

        # Regular member (non-admin) should only see their own tasks
        snapshot = _get_snapshot_for_date(mock_supabase, "tenant-1", "user-1", "member", target_date)
        assert snapshot.total_tasks == 5  # Only user-1's tasks

        # org_admin should see all tasks
        snapshot_admin = _get_snapshot_for_date(mock_supabase, "tenant-1", "user-1", "org_admin", target_date)
        assert snapshot_admin.total_tasks == 8  # All tasks


def test_get_dashboard_summary_includes_comparative_snapshots():
    """Test that get_dashboard_summary includes yesterday, last week, and last month snapshots."""
    from datetime import datetime, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    # Mock current state
    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    mock_tasks = [
        TaskResponse(id=f"t{i}", title=f"Task {i}", project_id="proj-1", status_id="status-1", assignee_id="user-1")
        for i in range(10)
    ]

    mock_statuses = [MockStatus("status-1", "To Do")]
    mock_attendance = [Mock(id=f"att{i}") for i in range(5)]

    # Mock the _get_snapshot_for_date calls with different values using actual ComparisonSnapshot objects
    mock_yesterday_snapshot = ComparisonSnapshot(total_sites=1, total_wallet_balance=900.0, total_tasks=9, total_today_present=4)
    mock_week_snapshot = ComparisonSnapshot(total_sites=1, total_wallet_balance=800.0, total_tasks=8, total_today_present=5)
    mock_month_snapshot = ComparisonSnapshot(total_sites=1, total_wallet_balance=700.0, total_tasks=7, total_today_present=3)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=1000.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=mock_attendance), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", side_effect=[
             mock_yesterday_snapshot,
             mock_week_snapshot,
             mock_month_snapshot,
         ]):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        # Verify snapshots are populated
        assert result.yesterday_snapshot is not None
        assert result.yesterday_snapshot.total_sites == 1
        assert result.yesterday_snapshot.total_wallet_balance == 900.0
        assert result.yesterday_snapshot.total_tasks == 9
        assert result.yesterday_snapshot.total_today_present == 4

        assert result.last_week_snapshot is not None
        assert result.last_week_snapshot.total_sites == 1
        assert result.last_week_snapshot.total_wallet_balance == 800.0
        assert result.last_week_snapshot.total_tasks == 8
        assert result.last_week_snapshot.total_today_present == 5

        assert result.last_month_snapshot is not None
        assert result.last_month_snapshot.total_sites == 1
        assert result.last_month_snapshot.total_wallet_balance == 700.0
        assert result.last_month_snapshot.total_tasks == 7
        assert result.last_month_snapshot.total_today_present == 3


def test_get_snapshot_for_date_date_format():
    """Test that snapshot calculation receives correctly formatted dates."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()
    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    mock_tasks = []
    mock_statuses = []
    mock_attendance = []

    # Capture the dates passed to _get_snapshot_for_date
    called_dates = []

    def mock_get_snapshot(supabase, tenant_id, user_id, tenant_role, target_date):
        called_dates.append(target_date)
        return ComparisonSnapshot(total_sites=0, total_wallet_balance=0.0, total_tasks=0, total_today_present=0)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=mock_attendance), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", side_effect=mock_get_snapshot):

        get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        # Verify date formats are YYYY-MM-DD
        assert len(called_dates) == 3
        for date_str in called_dates:
            assert len(date_str) == 10  # YYYY-MM-DD format
            assert date_str[4] == "-"
            assert date_str[7] == "-"
            # Verify it's a valid date
            datetime.strptime(date_str, "%Y-%m-%d")

        # Verify date calculations
        today = datetime.now(timezone.utc)
        expected_yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        expected_week = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        expected_month = (today - timedelta(days=30)).strftime("%Y-%m-%d")

        assert called_dates[0] == expected_yesterday
        assert called_dates[1] == expected_week
        assert called_dates[2] == expected_month


def test_get_snapshot_for_date_rounds_wallet_balance():
    """Test that wallet balance is rounded to 2 decimal places in snapshots."""
    from datetime import datetime, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import _get_snapshot_for_date
    from app.modules.projects.schemas import ProjectResponse

    target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
        ProjectResponse(id="proj-2", tenant_id="tenant-1", name="Site B", timezone="Asia/Kolkata", address="Location B"),
    ]

    mock_tasks = []
    mock_attendance = []

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", side_effect=[123.456789, 234.567891]), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_attendance", return_value=mock_attendance):

        snapshot = _get_snapshot_for_date(mock_supabase, "tenant-1", "user-1", "org_admin", target_date)

        # 123.456789 + 234.567891 = 358.02468, rounded to 358.02
        assert snapshot.total_wallet_balance == 358.02


def test_get_labour_trends_basic_calculation():
    """Test basic labour trends calculation with multiple projects and dates."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_labour_trends
    from app.modules.projects.schemas import ProjectResponse

    mock_supabase = Mock()

    # Mock two accessible projects
    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
        ProjectResponse(id="proj-2", tenant_id="tenant-1", name="Site B", timezone="Asia/Kolkata", address="Location B"),
    ]

    today = datetime.now(timezone.utc)
    date_1 = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    date_2 = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    date_3 = today.strftime("%Y-%m-%d")

    # Mock labour records for project 1
    mock_labour_proj1 = [
        {
            "date": date_1,
            "count": 5,
            "labour_types": {"name": "Mason", "rate_per_day": 500.0},
        },
        {
            "date": date_1,
            "count": 3,
            "labour_types": {"name": "Helper", "rate_per_day": 300.0},
        },
        {
            "date": date_2,
            "count": 4,
            "labour_types": {"name": "Mason", "rate_per_day": 500.0},
        },
    ]

    # Mock labour records for project 2
    mock_labour_proj2 = [
        {
            "date": date_2,
            "count": 2,
            "labour_types": {"name": "Electrician", "rate_per_day": 600.0},
        },
        {
            "date": date_3,
            "count": 6,
            "labour_types": {"name": "Plumber", "rate_per_day": 550.0},
        },
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_labour_in_range", side_effect=[mock_labour_proj1, mock_labour_proj2]):

        result = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin", period_days=30)

        assert result.period_days == 30
        assert len(result.data) == 3

        # Sort by date to verify calculations
        data_by_date = {dp.date: dp for dp in result.data}

        # date_1: proj1 has (5*500 + 3*300) = 2500 + 900 = 3400, workers = 5+3 = 8
        assert data_by_date[date_1].total_payment == 3400.0
        assert data_by_date[date_1].worker_count == 8

        # date_2: proj1 has (4*500) = 2000, proj2 has (2*600) = 1200, total = 3200, workers = 4+2 = 6
        assert data_by_date[date_2].total_payment == 3200.0
        assert data_by_date[date_2].worker_count == 6

        # date_3: proj2 has (6*550) = 3300, workers = 6
        assert data_by_date[date_3].total_payment == 3300.0
        assert data_by_date[date_3].worker_count == 6

        # Verify chronological order
        assert result.data[0].date == date_1
        assert result.data[1].date == date_2
        assert result.data[2].date == date_3


def test_get_labour_trends_role_based_filtering():
    """Test that labour trends respects role-based project access."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_labour_trends
    from app.modules.projects.schemas import ProjectResponse

    mock_supabase = Mock()
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%Y-%m-%d")

    # Member only has access to 1 project
    member_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # Admin has access to 2 projects
    admin_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
        ProjectResponse(id="proj-2", tenant_id="tenant-1", name="Site B", timezone="Asia/Kolkata", address="Location B"),
    ]

    mock_labour_proj1 = [
        {"date": date_str, "count": 5, "labour_types": {"name": "Mason", "rate_per_day": 500.0}},
    ]

    mock_labour_proj2 = [
        {"date": date_str, "count": 3, "labour_types": {"name": "Helper", "rate_per_day": 300.0}},
    ]

    # Test member access (only sees proj-1)
    with patch("app.modules.dashboard.service.list_projects", return_value=member_projects), \
         patch("app.modules.dashboard.service.list_labour_in_range", return_value=mock_labour_proj1):

        member_result = get_labour_trends(mock_supabase, "tenant-1", "user-1", "member", period_days=7)

        assert len(member_result.data) == 1
        assert member_result.data[0].total_payment == 2500.0  # 5 * 500
        assert member_result.data[0].worker_count == 5

    # Test admin access (sees both projects)
    with patch("app.modules.dashboard.service.list_projects", return_value=admin_projects), \
         patch("app.modules.dashboard.service.list_labour_in_range", side_effect=[mock_labour_proj1, mock_labour_proj2]):

        admin_result = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin", period_days=7)

        assert len(admin_result.data) == 1
        assert admin_result.data[0].total_payment == 3400.0  # (5*500) + (3*300)
        assert admin_result.data[0].worker_count == 8  # 5 + 3


def test_get_labour_trends_different_period_days():
    """Test that different period_days values are reflected in the response."""
    from datetime import datetime, timezone
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_labour_trends
    from app.modules.projects.schemas import ProjectResponse

    mock_supabase = Mock()
    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_labour_in_range", return_value=[]):

        # Test 7 days
        result_7 = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin", period_days=7)
        assert result_7.period_days == 7

        # Test 30 days (default)
        result_30 = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin")
        assert result_30.period_days == 30

        # Test 90 days
        result_90 = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin", period_days=90)
        assert result_90.period_days == 90


def test_get_labour_trends_empty_data():
    """Test labour trends with no labour records."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_labour_trends
    from app.modules.projects.schemas import ProjectResponse

    mock_supabase = Mock()

    # Test with projects but no labour records
    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_labour_in_range", return_value=[]):

        result = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin", period_days=30)

        assert result.period_days == 30
        assert len(result.data) == 0


def test_get_labour_trends_no_accessible_projects():
    """Test labour trends when user has no accessible projects."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_labour_trends

    mock_supabase = Mock()

    with patch("app.modules.dashboard.service.list_projects", return_value=[]):

        result = get_labour_trends(mock_supabase, "tenant-1", "user-1", "member", period_days=30)

        assert result.period_days == 30
        assert len(result.data) == 0


def test_get_labour_trends_handles_date_objects():
    """Test that labour trends correctly handles date objects from database."""
    from datetime import datetime, timedelta, timezone, date as date_type
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_labour_trends
    from app.modules.projects.schemas import ProjectResponse

    mock_supabase = Mock()
    today = datetime.now(timezone.utc)
    date_obj = (today - timedelta(days=1)).date()  # Python date object

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # Mock labour record with date as date object (not string)
    mock_labour = [
        {
            "date": date_obj,  # Date object, not string
            "count": 4,
            "labour_types": {"name": "Mason", "rate_per_day": 500.0},
        },
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_labour_in_range", return_value=mock_labour):

        result = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin", period_days=7)

        assert len(result.data) == 1
        assert result.data[0].date == date_obj.strftime("%Y-%m-%d")
        assert result.data[0].total_payment == 2000.0
        assert result.data[0].worker_count == 4


def test_get_labour_trends_rounds_payment_to_2_decimals():
    """Test that payment amounts are rounded to 2 decimal places."""
    from datetime import datetime, timezone
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_labour_trends
    from app.modules.projects.schemas import ProjectResponse

    mock_supabase = Mock()
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%Y-%m-%d")

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # Mock labour with rate that produces fractional cents
    mock_labour = [
        {
            "date": date_str,
            "count": 3,
            "labour_types": {"name": "Mason", "rate_per_day": 333.33},  # 3 * 333.33 = 999.99
        },
        {
            "date": date_str,
            "count": 1,
            "labour_types": {"name": "Helper", "rate_per_day": 0.01},  # Edge case: very small amount
        },
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_labour_in_range", return_value=mock_labour):

        result = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin", period_days=7)

        assert len(result.data) == 1
        # 999.99 + 0.01 = 1000.00
        assert result.data[0].total_payment == 1000.0
        assert result.data[0].worker_count == 4


def test_get_labour_trends_skips_records_without_date():
    """Test that labour trends skips records missing date field."""
    from datetime import datetime, timezone
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_labour_trends
    from app.modules.projects.schemas import ProjectResponse

    mock_supabase = Mock()
    today = datetime.now(timezone.utc)
    date_str = today.strftime("%Y-%m-%d")

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    mock_labour = [
        {
            "date": date_str,
            "count": 5,
            "labour_types": {"name": "Mason", "rate_per_day": 500.0},
        },
        {
            # Missing date field - should be skipped
            "count": 3,
            "labour_types": {"name": "Helper", "rate_per_day": 300.0},
        },
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_labour_in_range", return_value=mock_labour):

        result = get_labour_trends(mock_supabase, "tenant-1", "user-1", "org_admin", period_days=7)

        assert len(result.data) == 1
        # Should only include the first record with valid date
        assert result.data[0].total_payment == 2500.0  # 5 * 500
        assert result.data[0].worker_count == 5


def test_get_material_alerts_basic_detection():
    """Test basic material alerts detection with low stock materials."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_material_alerts
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse

    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
        ProjectResponse(id="proj-2", tenant_id="tenant-1", name="Site B", timezone="Asia/Kolkata", address="Location B"),
    ]

    # Mock materials for project 1: one low stock, one normal
    mock_materials_proj1 = [
        MaterialWithBalanceResponse(
            id="mat-1",
            project_id="proj-1",
            name="Cement",
            unit="bags",
            balance=5.0,  # Below threshold of 20
        ),
        MaterialWithBalanceResponse(
            id="mat-2",
            project_id="proj-1",
            name="Steel Rods",
            unit="tons",
            balance=50.0,  # Above threshold
        ),
    ]

    # Mock materials for project 2: all low stock
    mock_materials_proj2 = [
        MaterialWithBalanceResponse(
            id="mat-3",
            project_id="proj-2",
            name="Bricks",
            unit="units",
            balance=10.0,  # Below threshold
        ),
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_materials_with_balance", side_effect=[mock_materials_proj1, mock_materials_proj2]):

        result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "org_admin")

        assert result.total_alerts == 2
        assert len(result.alerts) == 2

        # Verify alerts are sorted by balance (lowest first)
        assert result.alerts[0].current_balance == 5.0
        assert result.alerts[0].material_name == "Cement"
        assert result.alerts[0].project_name == "Site A"
        assert result.alerts[0].threshold == 20.0
        assert result.alerts[0].alert_level == "low"

        assert result.alerts[1].current_balance == 10.0
        assert result.alerts[1].material_name == "Bricks"
        assert result.alerts[1].project_name == "Site B"


def test_get_material_alerts_role_based_filtering():
    """Test that material alerts respect role-based project access."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_material_alerts
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse

    mock_supabase = Mock()

    # Member only has access to 1 project
    member_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # Admin has access to 2 projects
    admin_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
        ProjectResponse(id="proj-2", tenant_id="tenant-1", name="Site B", timezone="Asia/Kolkata", address="Location B"),
    ]

    # Both projects have low stock materials
    mock_materials_proj1 = [
        MaterialWithBalanceResponse(
            id="mat-1", project_id="proj-1", name="Cement", unit="bags", balance=5.0
        ),
    ]

    mock_materials_proj2 = [
        MaterialWithBalanceResponse(
            id="mat-2", project_id="proj-2", name="Bricks", unit="units", balance=10.0
        ),
    ]

    # Test member access (only sees proj-1)
    with patch("app.modules.dashboard.service.list_projects", return_value=member_projects), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=mock_materials_proj1):

        member_result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "member")

        assert member_result.total_alerts == 1
        assert member_result.alerts[0].material_name == "Cement"
        assert member_result.alerts[0].project_name == "Site A"

    # Test admin access (sees both projects)
    with patch("app.modules.dashboard.service.list_projects", return_value=admin_projects), \
         patch("app.modules.dashboard.service.list_materials_with_balance", side_effect=[mock_materials_proj1, mock_materials_proj2]):

        admin_result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "org_admin")

        assert admin_result.total_alerts == 2
        assert {alert.material_name for alert in admin_result.alerts} == {"Cement", "Bricks"}


def test_get_material_alerts_threshold_comparison():
    """Test threshold comparison logic - only materials with balance < threshold."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_material_alerts
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse

    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # Materials at various threshold boundaries (threshold = 20.0)
    mock_materials = [
        MaterialWithBalanceResponse(
            id="mat-1", project_id="proj-1", name="Below Threshold", unit="units", balance=19.99  # Alert
        ),
        MaterialWithBalanceResponse(
            id="mat-2", project_id="proj-1", name="At Threshold", unit="units", balance=20.0  # No alert
        ),
        MaterialWithBalanceResponse(
            id="mat-3", project_id="proj-1", name="Above Threshold", unit="units", balance=20.01  # No alert
        ),
        MaterialWithBalanceResponse(
            id="mat-4", project_id="proj-1", name="Zero Balance", unit="units", balance=0.0  # Alert
        ),
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=mock_materials):

        result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "org_admin")

        assert result.total_alerts == 2
        # Only materials with balance < 20.0
        alert_names = {alert.material_name for alert in result.alerts}
        assert alert_names == {"Below Threshold", "Zero Balance"}


def test_get_material_alerts_no_projects():
    """Test material alerts when user has no accessible projects."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_material_alerts

    mock_supabase = Mock()

    with patch("app.modules.dashboard.service.list_projects", return_value=[]):

        result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "member")

        assert result.total_alerts == 0
        assert len(result.alerts) == 0


def test_get_material_alerts_no_materials():
    """Test material alerts when projects have no materials."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_material_alerts
    from app.modules.projects.schemas import ProjectResponse

    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]):

        result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "org_admin")

        assert result.total_alerts == 0
        assert len(result.alerts) == 0


def test_get_material_alerts_no_low_stock():
    """Test material alerts when all materials have sufficient stock."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_material_alerts
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse

    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # All materials have sufficient stock (above threshold of 20)
    mock_materials = [
        MaterialWithBalanceResponse(
            id="mat-1", project_id="proj-1", name="Cement", unit="bags", balance=100.0
        ),
        MaterialWithBalanceResponse(
            id="mat-2", project_id="proj-1", name="Steel", unit="tons", balance=50.0
        ),
        MaterialWithBalanceResponse(
            id="mat-3", project_id="proj-1", name="Bricks", unit="units", balance=1000.0
        ),
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=mock_materials):

        result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "org_admin")

        assert result.total_alerts == 0
        assert len(result.alerts) == 0


def test_get_material_alerts_sorting():
    """Test that alerts are sorted by balance (lowest first)."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_material_alerts
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse

    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # Materials with various low balances
    mock_materials = [
        MaterialWithBalanceResponse(
            id="mat-1", project_id="proj-1", name="Medium Stock", unit="units", balance=15.0
        ),
        MaterialWithBalanceResponse(
            id="mat-2", project_id="proj-1", name="Lowest Stock", unit="units", balance=2.5
        ),
        MaterialWithBalanceResponse(
            id="mat-3", project_id="proj-1", name="Low Stock", unit="units", balance=8.0
        ),
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=mock_materials):

        result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "org_admin")

        assert result.total_alerts == 3
        # Verify sorted by balance (ascending)
        assert result.alerts[0].current_balance == 2.5
        assert result.alerts[0].material_name == "Lowest Stock"
        assert result.alerts[1].current_balance == 8.0
        assert result.alerts[1].material_name == "Low Stock"
        assert result.alerts[2].current_balance == 15.0
        assert result.alerts[2].material_name == "Medium Stock"


def test_get_material_alerts_includes_all_fields():
    """Test that material alert items include all required fields."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_material_alerts
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse

    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-123", tenant_id="tenant-1", name="Construction Site Alpha", timezone="Asia/Kolkata", address="Location A"),
    ]

    mock_materials = [
        MaterialWithBalanceResponse(
            id="mat-456",
            project_id="proj-123",
            name="Portland Cement",
            unit="bags",
            balance=12.5,
        ),
    ]

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=mock_materials):

        result = get_material_alerts(mock_supabase, "tenant-1", "user-1", "org_admin")

        assert result.total_alerts == 1
        alert = result.alerts[0]

        # Verify all fields are populated correctly
        assert alert.project_id == "proj-123"
        assert alert.project_name == "Construction Site Alpha"
        assert alert.material_id == "mat-456"
        assert alert.material_name == "Portland Cement"
        assert alert.current_balance == 12.5
        assert alert.unit == "bags"
        assert alert.threshold == 20.0
        assert alert.alert_level == "low"


def test_get_dashboard_summary_populates_material_alerts_count():
    """Test that get_dashboard_summary correctly populates material_alerts_count."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    # Mock projects
    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
        ProjectResponse(id="proj-2", tenant_id="tenant-1", name="Site B", timezone="Asia/Kolkata", address="Location B"),
    ]

    # Mock materials with low stock for the two projects
    mock_materials_proj1 = [
        MaterialWithBalanceResponse(
            id="mat-1", project_id="proj-1", name="Cement", unit="bags", balance=5.0
        ),
        MaterialWithBalanceResponse(
            id="mat-2", project_id="proj-1", name="Steel", unit="tons", balance=15.0
        ),
    ]

    mock_materials_proj2 = [
        MaterialWithBalanceResponse(
            id="mat-3", project_id="proj-2", name="Bricks", unit="units", balance=10.0
        ),
    ]

    mock_tasks = []
    mock_statuses = [MockStatus("status-1", "To Do")]
    mock_attendance = []

    # Mock snapshots
    mock_snapshot = ComparisonSnapshot(
        total_sites=2, total_wallet_balance=1000.0, total_tasks=0, total_today_present=0
    )

    # list_materials_with_balance is called 4 times: once per project in loop, once per project in get_material_alerts
    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=500.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=mock_attendance), \
         patch("app.modules.dashboard.service.list_materials_with_balance", side_effect=[
             mock_materials_proj1,  # First project in main loop
             mock_materials_proj2,  # Second project in main loop
             mock_materials_proj1,  # First project in get_material_alerts
             mock_materials_proj2,  # Second project in get_material_alerts
         ]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        # Verify material_alerts_count is populated with actual count (3 materials below threshold of 20)
        assert result.material_alerts_count == 3


def test_get_dashboard_summary_material_alerts_count_zero_when_no_alerts():
    """Test that material_alerts_count is 0 when there are no low stock materials."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
    ]

    # All materials have sufficient stock (above threshold)
    mock_materials = [
        MaterialWithBalanceResponse(
            id="mat-1", project_id="proj-1", name="Cement", unit="bags", balance=100.0
        ),
        MaterialWithBalanceResponse(
            id="mat-2", project_id="proj-1", name="Steel", unit="tons", balance=50.0
        ),
    ]

    mock_tasks = []
    mock_statuses = [MockStatus("status-1", "To Do")]
    mock_attendance = []

    mock_snapshot = ComparisonSnapshot(
        total_sites=1, total_wallet_balance=500.0, total_tasks=0, total_today_present=0
    )

    # list_materials_with_balance is called twice: once in main loop, once in get_material_alerts
    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=500.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=mock_attendance), \
         patch("app.modules.dashboard.service.list_materials_with_balance", side_effect=[mock_materials, mock_materials]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        # Verify material_alerts_count is 0 when no materials are below threshold
        assert result.material_alerts_count == 0


def test_get_dashboard_summary_integrates_health_calculation():
    """Test that dashboard integrates with health.py for calculating project health."""
    from datetime import date, datetime, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    # Mock project with lifecycle dates
    today = date.today()
    start = today - timedelta(days=50)
    end = today + timedelta(days=50)  # 100-day project, 50% time elapsed

    mock_projects = [
        ProjectResponse(
            id="proj-1",
            tenant_id="tenant-1",
            name="Site A",
            timezone="Asia/Kolkata",
            address="Location A",
            status="active",
            start_date=start,
            end_date=end,
        ),
    ]

    # 10 total tasks, 7 completed = 70% task completion
    # At 50% time elapsed with 70% tasks done → should be "on_track"
    mock_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-1") for i in range(7)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-1") for i in range(7, 10)],
    ]

    mock_statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    mock_attendance = []
    mock_materials = []
    mock_snapshot = ComparisonSnapshot(total_sites=1, total_wallet_balance=0.0, total_tasks=10, total_today_present=0)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=mock_attendance), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=mock_materials), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        assert len(result.projects) == 1
        project = result.projects[0]

        # Verify health calculation from health.py is used
        assert project.status == "on_track"
        assert project.task_completion_percentage == 70.0


def test_get_dashboard_summary_health_at_risk():
    """Test dashboard correctly identifies at-risk projects using health.py logic."""
    from datetime import date, datetime, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    # Project with 80% time elapsed
    today = date.today()
    start = today - timedelta(days=80)
    end = today + timedelta(days=20)  # 100-day project, 80% time elapsed

    mock_projects = [
        ProjectResponse(
            id="proj-1",
            tenant_id="tenant-1",
            name="Site A",
            timezone="Asia/Kolkata",
            address="Location A",
            status="active",
            start_date=start,
            end_date=end,
        ),
    ]

    # 10 total tasks, 5 completed = 50% task completion
    # At 80% time elapsed with 50% tasks done → should be "at_risk"
    mock_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-1") for i in range(5)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-1") for i in range(5, 10)],
    ]

    mock_statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    mock_snapshot = ComparisonSnapshot(total_sites=1, total_wallet_balance=0.0, total_tasks=10, total_today_present=0)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=[]), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        project = result.projects[0]
        assert project.status == "at_risk"
        assert project.task_completion_percentage == 50.0


def test_get_dashboard_summary_health_delayed():
    """Test dashboard correctly identifies delayed projects using health.py logic."""
    from datetime import date, datetime, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    # Project past end date
    today = date.today()
    start = today - timedelta(days=100)
    end = today - timedelta(days=10)  # Project ended 10 days ago

    mock_projects = [
        ProjectResponse(
            id="proj-1",
            tenant_id="tenant-1",
            name="Site A",
            timezone="Asia/Kolkata",
            address="Location A",
            status="active",
            start_date=start,
            end_date=end,
        ),
    ]

    # 10 total tasks, 6 completed = 60% (not finished yet project is past deadline)
    mock_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-1") for i in range(6)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-1") for i in range(6, 10)],
    ]

    mock_statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    mock_snapshot = ComparisonSnapshot(total_sites=1, total_wallet_balance=0.0, total_tasks=10, total_today_present=0)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=[]), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        project = result.projects[0]
        assert project.status == "delayed"


def test_get_dashboard_summary_health_without_dates():
    """Test dashboard handles projects without lifecycle dates gracefully."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    # Project without start/end dates
    mock_projects = [
        ProjectResponse(
            id="proj-1",
            tenant_id="tenant-1",
            name="Site A",
            timezone="Asia/Kolkata",
            address="Location A",
            status="planning",
            start_date=None,
            end_date=None,
        ),
    ]

    # With 8 tasks completed out of 10, completion is 80% -> on_track
    mock_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-1") for i in range(8)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-1") for i in range(8, 10)],
    ]

    mock_statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    mock_snapshot = ComparisonSnapshot(total_sites=1, total_wallet_balance=0.0, total_tasks=10, total_today_present=0)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=[]), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        project = result.projects[0]
        # Without dates, uses fallback task-based calculation (80% = on_track)
        assert project.status == "on_track"
        assert project.task_completion_percentage == 80.0


def test_get_dashboard_summary_per_project_material_alerts():
    """Test that each project gets its own material alert count."""
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.materials.schemas import MaterialWithBalanceResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    mock_projects = [
        ProjectResponse(id="proj-1", tenant_id="tenant-1", name="Site A", timezone="Asia/Kolkata", address="Location A"),
        ProjectResponse(id="proj-2", tenant_id="tenant-1", name="Site B", timezone="Asia/Kolkata", address="Location B"),
    ]

    # Project 1: 2 low stock materials
    mock_materials_proj1 = [
        MaterialWithBalanceResponse(id="mat-1", project_id="proj-1", name="Cement", unit="bags", balance=5.0),
        MaterialWithBalanceResponse(id="mat-2", project_id="proj-1", name="Steel", unit="tons", balance=15.0),
        MaterialWithBalanceResponse(id="mat-3", project_id="proj-1", name="Bricks", unit="units", balance=100.0),  # Not low
    ]

    # Project 2: 1 low stock material
    mock_materials_proj2 = [
        MaterialWithBalanceResponse(id="mat-4", project_id="proj-2", name="Sand", unit="tons", balance=10.0),
        MaterialWithBalanceResponse(id="mat-5", project_id="proj-2", name="Gravel", unit="tons", balance=50.0),  # Not low
    ]

    mock_tasks = []
    mock_statuses = [MockStatus("status-1", "To Do")]
    mock_snapshot = ComparisonSnapshot(total_sites=2, total_wallet_balance=0.0, total_tasks=0, total_today_present=0)

    # list_materials_with_balance is called 4 times:
    # - once per project in the main loop (2 calls)
    # - once per project in get_material_alerts (2 calls)
    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=[]), \
         patch("app.modules.dashboard.service.list_materials_with_balance", side_effect=[
             mock_materials_proj1,  # First project in main loop
             mock_materials_proj2,  # Second project in main loop
             mock_materials_proj1,  # First project in get_material_alerts
             mock_materials_proj2,  # Second project in get_material_alerts
         ]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        # Verify per-project material alerts
        proj1 = next(p for p in result.projects if p.project_id == "proj-1")
        proj2 = next(p for p in result.projects if p.project_id == "proj-2")

        assert proj1.material_alerts == 2
        assert proj2.material_alerts == 1

        # Total alerts should be sum of all
        assert result.material_alerts_count == 3


def test_get_dashboard_summary_includes_is_out_of_date():
    """Test that is_out_of_date field is populated using is_project_out_of_date()."""
    from datetime import date, timedelta, datetime
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    # Project 1: End date passed, should be out of date
    today = date.today()
    proj1_end = today - timedelta(days=5)

    # Project 2: End date in future, should not be out of date
    proj2_end = today + timedelta(days=30)

    # Project 3: No end date, should not be out of date
    mock_projects = [
        ProjectResponse(
            id="proj-1",
            tenant_id="tenant-1",
            name="Overdue Project",
            timezone="Asia/Kolkata",
            address="Location A",
            status="active",
            end_date=proj1_end,
            updated_at=datetime.now().isoformat(),
        ),
        ProjectResponse(
            id="proj-2",
            tenant_id="tenant-1",
            name="Active Project",
            timezone="Asia/Kolkata",
            address="Location B",
            status="active",
            end_date=proj2_end,
            updated_at=datetime.now().isoformat(),
        ),
        ProjectResponse(
            id="proj-3",
            tenant_id="tenant-1",
            name="No Date Project",
            timezone="Asia/Kolkata",
            address="Location C",
            status="planning",
            end_date=None,
        ),
    ]

    mock_tasks = []
    mock_statuses = [MockStatus("status-1", "To Do")]
    mock_snapshot = ComparisonSnapshot(total_sites=3, total_wallet_balance=0.0, total_tasks=0, total_today_present=0)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=[]), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        # Verify is_out_of_date field is populated correctly
        proj1 = next(p for p in result.projects if p.project_id == "proj-1")
        proj2 = next(p for p in result.projects if p.project_id == "proj-2")
        proj3 = next(p for p in result.projects if p.project_id == "proj-3")

        assert proj1.is_out_of_date is True  # End date passed
        assert proj2.is_out_of_date is False  # End date in future
        assert proj3.is_out_of_date is False  # No end date


def test_get_dashboard_summary_health_distribution_counts():
    """Test that dashboard includes health distribution totals."""
    from datetime import date, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    # Create projects with different health statuses
    today = date.today()
    start = today - timedelta(days=50)

    # Project 1: On track (80% time, 70% completion)
    proj1_end = today + timedelta(days=50)
    proj1_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-1") for i in range(7)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-1") for i in range(7, 10)],
    ]

    # Project 2: At risk (80% time, 50% completion)
    proj2_start = today - timedelta(days=80)
    proj2_end = today + timedelta(days=20)
    proj2_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-2") for i in range(5)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-2") for i in range(5, 10)],
    ]

    # Project 3: Delayed (past end date)
    proj3_start = today - timedelta(days=100)
    proj3_end = today - timedelta(days=10)
    proj3_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-3") for i in range(6)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-3") for i in range(6, 10)],
    ]

    # Project 4: Another on track
    proj4_end = today + timedelta(days=100)
    proj4_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-4") for i in range(8)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-4") for i in range(8, 10)],
    ]

    mock_projects = [
        ProjectResponse(
            id="proj-1",
            tenant_id="tenant-1",
            name="Project A",
            timezone="Asia/Kolkata",
            address="Location A",
            status="active",
            start_date=start,
            end_date=proj1_end,
        ),
        ProjectResponse(
            id="proj-2",
            tenant_id="tenant-1",
            name="Project B",
            timezone="Asia/Kolkata",
            address="Location B",
            status="active",
            start_date=proj2_start,
            end_date=proj2_end,
        ),
        ProjectResponse(
            id="proj-3",
            tenant_id="tenant-1",
            name="Project C",
            timezone="Asia/Kolkata",
            address="Location C",
            status="active",
            start_date=proj3_start,
            end_date=proj3_end,
        ),
        ProjectResponse(
            id="proj-4",
            tenant_id="tenant-1",
            name="Project D",
            timezone="Asia/Kolkata",
            address="Location D",
            status="active",
            start_date=start,
            end_date=proj4_end,
        ),
    ]

    mock_statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    mock_snapshot = ComparisonSnapshot(total_sites=4, total_wallet_balance=0.0, total_tasks=40, total_today_present=0)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", side_effect=[proj1_tasks, proj2_tasks, proj3_tasks, proj4_tasks]), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=[]), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        # Verify health distribution counts
        assert result.projects_on_track_count == 2  # proj-1 and proj-4
        assert result.projects_at_risk_count == 1   # proj-2
        assert result.projects_delayed_count == 1   # proj-3
        assert result.total_sites == 4


def test_get_dashboard_summary_health_distribution_all_on_track():
    """Test health distribution when all projects are on track."""
    from datetime import date, timedelta
    from unittest.mock import Mock, patch
    from app.modules.dashboard.service import get_dashboard_summary
    from app.modules.projects.schemas import ProjectResponse
    from app.modules.dashboard.schemas import ComparisonSnapshot

    mock_supabase = Mock()

    today = date.today()
    start = today - timedelta(days=30)
    end = today + timedelta(days=70)

    # All projects have good completion rates
    mock_projects = [
        ProjectResponse(
            id=f"proj-{i}",
            tenant_id="tenant-1",
            name=f"Project {i}",
            timezone="Asia/Kolkata",
            address=f"Location {i}",
            status="active",
            start_date=start,
            end_date=end,
        )
        for i in range(3)
    ]

    # 80% completion for all
    mock_tasks = [
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-2", project_id="proj-1") for i in range(8)],
        *[TaskResponse(id=f"t{i}", title=f"Task {i}", status_id="status-1", project_id="proj-1") for i in range(8, 10)],
    ]

    mock_statuses = [
        MockStatus("status-1", "To Do"),
        MockStatus("status-2", "Done"),
    ]

    mock_snapshot = ComparisonSnapshot(total_sites=3, total_wallet_balance=0.0, total_tasks=30, total_today_present=0)

    with patch("app.modules.dashboard.service.list_projects", return_value=mock_projects), \
         patch("app.modules.dashboard.service.get_balance", return_value=0.0), \
         patch("app.modules.dashboard.service.list_tasks", return_value=mock_tasks), \
         patch("app.modules.dashboard.service.list_statuses", return_value=mock_statuses), \
         patch("app.modules.dashboard.service.list_attendance", return_value=[]), \
         patch("app.modules.dashboard.service.list_materials_with_balance", return_value=[]), \
         patch("app.modules.dashboard.service._get_snapshot_for_date", return_value=mock_snapshot):

        result = get_dashboard_summary(mock_supabase, "tenant-1", "user-1", "org_admin")

        # All should be on track
        assert result.projects_on_track_count == 3
        assert result.projects_at_risk_count == 0
        assert result.projects_delayed_count == 0
