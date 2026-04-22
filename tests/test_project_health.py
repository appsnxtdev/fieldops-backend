"""Tests for project health calculation logic."""
from datetime import date, datetime, timedelta
import pytest

from app.modules.projects.health import (
    calculate_project_health,
    is_project_out_of_date,
)


class TestCalculateProjectHealth:
    """Test calculate_project_health() function."""

    def test_on_track_project(self):
        """Test project that is on track."""
        # Project: 100 days, 50 days elapsed (50%), 10 tasks, 6 completed (60%)
        # Progress (60%) >= expected (50%) → on_track
        start_date = date.today() - timedelta(days=50)
        end_date = date.today() + timedelta(days=50)

        result = calculate_project_health(
            start_date=start_date,
            end_date=end_date,
            total_tasks=10,
            completed_tasks=6,
        )

        assert result == "on_track"

    def test_delayed_project_past_deadline(self):
        """Test project that is past its deadline."""
        # End date is in the past → delayed
        start_date = date.today() - timedelta(days=100)
        end_date = date.today() - timedelta(days=10)

        result = calculate_project_health(
            start_date=start_date,
            end_date=end_date,
            total_tasks=10,
            completed_tasks=5,
        )

        assert result == "delayed"

    def test_delayed_project_low_completion(self):
        """Test project that is delayed due to low task completion."""
        # 50% time elapsed but only 20% tasks done → delayed
        start_date = date.today() - timedelta(days=50)
        end_date = date.today() + timedelta(days=50)

        result = calculate_project_health(
            start_date=start_date,
            end_date=end_date,
            total_tasks=10,
            completed_tasks=2,
        )

        assert result == "delayed"

    def test_at_risk_project(self):
        """Test project that is at risk."""
        # 80% time elapsed, 55% tasks done → at_risk (< 60%)
        start_date = date.today() - timedelta(days=80)
        end_date = date.today() + timedelta(days=20)

        result = calculate_project_health(
            start_date=start_date,
            end_date=end_date,
            total_tasks=100,
            completed_tasks=55,
        )

        assert result == "at_risk"

    def test_none_when_zero_tasks(self):
        """Test returns None when total_tasks is 0."""
        start_date = date.today() - timedelta(days=50)
        end_date = date.today() + timedelta(days=50)

        result = calculate_project_health(
            start_date=start_date,
            end_date=end_date,
            total_tasks=0,
            completed_tasks=0,
        )

        assert result is None

    def test_none_when_completed_equals_total(self):
        """Test returns None when all tasks are completed."""
        start_date = date.today() - timedelta(days=50)
        end_date = date.today() + timedelta(days=50)

        result = calculate_project_health(
            start_date=start_date,
            end_date=end_date,
            total_tasks=10,
            completed_tasks=10,
        )

        assert result is None

    def test_edge_case_at_risk_threshold(self):
        """Test exact at_risk threshold (80% time, 60% tasks)."""
        # Exactly at the boundary: 80% time, 60% tasks → on_track
        start_date = date.today() - timedelta(days=80)
        end_date = date.today() + timedelta(days=20)

        result = calculate_project_health(
            start_date=start_date,
            end_date=end_date,
            total_tasks=10,
            completed_tasks=6,
        )

        assert result == "on_track"


class TestIsProjectOutOfDate:
    """Test is_project_out_of_date() function."""

    def test_completed_project_not_out_of_date(self):
        """Test that completed projects are never considered out of date."""
        end_date = date.today() - timedelta(days=100)
        last_activity = datetime.now() - timedelta(days=100)

        result = is_project_out_of_date(
            end_date=end_date,
            last_activity_at=last_activity,
            status="completed",
        )

        assert result is False

    def test_project_past_end_date_is_out_of_date(self):
        """Test project past end date is out of date."""
        end_date = date.today() - timedelta(days=10)
        last_activity = datetime.now() - timedelta(days=5)

        result = is_project_out_of_date(
            end_date=end_date,
            last_activity_at=last_activity,
            status="active",
        )

        assert result is True

    def test_project_no_activity_30_days_is_out_of_date(self):
        """Test project with no activity for 30+ days is out of date."""
        end_date = date.today() + timedelta(days=50)
        last_activity = datetime.now() - timedelta(days=31)

        result = is_project_out_of_date(
            end_date=end_date,
            last_activity_at=last_activity,
            status="active",
        )

        assert result is True

    def test_project_with_recent_activity_not_out_of_date(self):
        """Test project with recent activity is not out of date."""
        end_date = date.today() + timedelta(days=50)
        last_activity = datetime.now() - timedelta(days=10)

        result = is_project_out_of_date(
            end_date=end_date,
            last_activity_at=last_activity,
            status="active",
        )

        assert result is False

    def test_none_last_activity_not_out_of_date(self):
        """Test project with no last_activity is not considered out of date."""
        end_date = date.today() + timedelta(days=50)

        result = is_project_out_of_date(
            end_date=end_date,
            last_activity_at=None,
            status="active",
        )

        assert result is False
