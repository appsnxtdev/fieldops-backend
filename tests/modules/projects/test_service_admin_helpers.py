"""Tests for project admin helper functions in service layer."""

import pytest
from unittest.mock import Mock, patch
from app.modules.projects.service import (
    get_user_admin_projects,
    get_project_members,
    check_user_in_project,
    is_project_admin,
    count_project_admins,
)
from app.modules.users.schemas import UserProfileResponse


class TestGetUserAdminProjects:
    """Tests for get_user_admin_projects helper function."""

    def test_returns_empty_list_when_user_has_no_admin_projects(self):
        """Test returns empty list when user is not admin of any project."""
        mock_supabase = Mock()

        # Mock project_members query - no admin memberships
        mock_execute = Mock()
        mock_execute.data = []

        mock_eq_role = Mock()
        mock_eq_role.execute.return_value = mock_execute

        mock_eq_user = Mock()
        mock_eq_user.eq.return_value = mock_eq_role

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_user

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = get_user_admin_projects(mock_supabase, "tenant-1", "user-1")

        assert result == []
        mock_schema.table.assert_called_with("project_members")

    def test_returns_projects_where_user_is_admin(self):
        """Test returns list of projects where user has admin role."""
        mock_supabase = Mock()

        # Mock project_members query - user is admin of 2 projects
        mock_members_execute = Mock()
        mock_members_execute.data = [
            {"project_id": "project-1"},
            {"project_id": "project-2"},
        ]

        mock_members_eq_role = Mock()
        mock_members_eq_role.execute.return_value = mock_members_execute

        mock_members_eq_user = Mock()
        mock_members_eq_user.eq.return_value = mock_members_eq_role

        mock_members_select = Mock()
        mock_members_select.eq.return_value = mock_members_eq_user

        # Mock projects query - get project details
        mock_projects_execute = Mock()
        mock_projects_execute.data = [
            {
                "id": "project-1",
                "tenant_id": "tenant-1",
                "name": "Project One",
                "timezone": "Asia/Kolkata",
                "created_at": "2026-04-01T10:00:00Z",
            },
            {
                "id": "project-2",
                "tenant_id": "tenant-1",
                "name": "Project Two",
                "timezone": "Asia/Kolkata",
                "created_at": "2026-04-02T10:00:00Z",
            },
        ]

        mock_projects_order = Mock()
        mock_projects_order.execute.return_value = mock_projects_execute

        mock_projects_in = Mock()
        mock_projects_in.order.return_value = mock_projects_order

        mock_projects_eq_tenant = Mock()
        mock_projects_eq_tenant.in_.return_value = mock_projects_in

        mock_projects_select = Mock()
        mock_projects_select.eq.return_value = mock_projects_eq_tenant

        # Setup table side effect
        def table_side_effect(name):
            if name == "project_members":
                mock_table = Mock()
                mock_table.select.return_value = mock_members_select
                return mock_table
            elif name == "projects":
                mock_table = Mock()
                mock_table.select.return_value = mock_projects_select
                return mock_table
            return Mock()

        mock_schema = Mock()
        mock_schema.table.side_effect = table_side_effect

        mock_supabase.schema.return_value = mock_schema

        result = get_user_admin_projects(mock_supabase, "tenant-1", "user-1")

        assert len(result) == 2
        assert result[0].id == "project-1"
        assert result[0].name == "Project One"
        assert result[1].id == "project-2"
        assert result[1].name == "Project Two"

    def test_enforces_tenant_isolation(self):
        """Test only returns projects from user's tenant."""
        mock_supabase = Mock()

        # Mock project_members query - user is admin of project
        mock_members_execute = Mock()
        mock_members_execute.data = [{"project_id": "project-other-tenant"}]

        mock_members_eq_role = Mock()
        mock_members_eq_role.execute.return_value = mock_members_execute

        mock_members_eq_user = Mock()
        mock_members_eq_user.eq.return_value = mock_members_eq_role

        mock_members_select = Mock()
        mock_members_select.eq.return_value = mock_members_eq_user

        # Mock projects query - empty because tenant filter blocks it
        mock_projects_execute = Mock()
        mock_projects_execute.data = []

        mock_projects_order = Mock()
        mock_projects_order.execute.return_value = mock_projects_execute

        mock_projects_in = Mock()
        mock_projects_in.order.return_value = mock_projects_order

        mock_projects_eq_tenant = Mock()
        mock_projects_eq_tenant.in_.return_value = mock_projects_in

        mock_projects_select = Mock()
        mock_projects_select.eq.return_value = mock_projects_eq_tenant

        # Setup table side effect
        def table_side_effect(name):
            if name == "project_members":
                mock_table = Mock()
                mock_table.select.return_value = mock_members_select
                return mock_table
            elif name == "projects":
                mock_table = Mock()
                mock_table.select.return_value = mock_projects_select
                return mock_table
            return Mock()

        mock_schema = Mock()
        mock_schema.table.side_effect = table_side_effect

        mock_supabase.schema.return_value = mock_schema

        result = get_user_admin_projects(mock_supabase, "tenant-1", "user-1")

        assert result == []

    def test_orders_by_created_at_descending(self):
        """Test results are ordered by created_at in descending order."""
        mock_supabase = Mock()

        # Mock project_members query
        mock_members_execute = Mock()
        mock_members_execute.data = [{"project_id": "project-1"}]

        mock_members_eq_role = Mock()
        mock_members_eq_role.execute.return_value = mock_members_execute

        mock_members_eq_user = Mock()
        mock_members_eq_user.eq.return_value = mock_members_eq_role

        mock_members_select = Mock()
        mock_members_select.eq.return_value = mock_members_eq_user

        # Mock projects query
        mock_projects_execute = Mock()
        mock_projects_execute.data = [
            {
                "id": "project-1",
                "tenant_id": "tenant-1",
                "name": "Project One",
                "timezone": "Asia/Kolkata",
            }
        ]

        mock_projects_order = Mock()
        mock_projects_order.execute.return_value = mock_projects_execute

        mock_projects_in = Mock()
        # Track order call
        order_calls = []

        def track_order(field, desc=False):
            order_calls.append({"field": field, "desc": desc})
            return mock_projects_order

        mock_projects_in.order.side_effect = track_order

        mock_projects_eq_tenant = Mock()
        mock_projects_eq_tenant.in_.return_value = mock_projects_in

        mock_projects_select = Mock()
        mock_projects_select.eq.return_value = mock_projects_eq_tenant

        # Setup table side effect
        def table_side_effect(name):
            if name == "project_members":
                mock_table = Mock()
                mock_table.select.return_value = mock_members_select
                return mock_table
            elif name == "projects":
                mock_table = Mock()
                mock_table.select.return_value = mock_projects_select
                return mock_table
            return Mock()

        mock_schema = Mock()
        mock_schema.table.side_effect = table_side_effect

        mock_supabase.schema.return_value = mock_schema

        result = get_user_admin_projects(mock_supabase, "tenant-1", "user-1")

        assert len(order_calls) == 1
        assert order_calls[0]["field"] == "created_at"
        assert order_calls[0]["desc"] is True


class TestGetProjectMembers:
    """Tests for get_project_members helper function."""

    def test_returns_empty_list_when_no_members(self):
        """Test returns empty list when project has no members."""
        mock_supabase = Mock()

        # Mock project_members query - no members
        mock_execute = Mock()
        mock_execute.data = []

        mock_order = Mock()
        mock_order.execute.return_value = mock_execute

        mock_eq = Mock()
        mock_eq.order.return_value = mock_order

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = get_project_members(mock_supabase, "project-1")

        assert result == []
        mock_schema.table.assert_called_with("project_members")

    def test_returns_members_with_enriched_user_info(self):
        """Test returns members with user profile information."""
        mock_supabase = Mock()

        # Mock project_members query
        mock_execute = Mock()
        mock_execute.data = [
            {
                "user_id": "user-1",
                "role": "admin",
                "created_at": "2026-04-01T10:00:00Z",
            },
            {
                "user_id": "user-2",
                "role": "member",
                "created_at": "2026-04-02T10:00:00Z",
            },
        ]

        mock_order = Mock()
        mock_order.execute.return_value = mock_execute

        mock_eq = Mock()
        mock_eq.order.return_value = mock_order

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        # Mock get_profiles_by_ids
        mock_profiles = [
            UserProfileResponse(
                id="user-1",
                email="user1@example.com",
                full_name="John Doe",
                avatar_url="https://example.com/avatar1.jpg",
            ),
            UserProfileResponse(
                id="user-2",
                email="user2@example.com",
                full_name="Jane Smith",
                avatar_url="https://example.com/avatar2.jpg",
            ),
        ]

        with patch(
            "app.modules.users.service.get_profiles_by_ids",
            return_value=mock_profiles,
        ):
            result = get_project_members(mock_supabase, "project-1")

        assert len(result) == 2
        assert result[0].project_id == "project-1"
        assert result[0].user_id == "user-1"
        assert result[0].role == "admin"
        assert result[0].user_email == "user1@example.com"
        assert result[0].user_full_name == "John Doe"
        assert result[0].user_avatar_url == "https://example.com/avatar1.jpg"

        assert result[1].user_id == "user-2"
        assert result[1].role == "member"
        assert result[1].user_email == "user2@example.com"
        assert result[1].user_full_name == "Jane Smith"

    def test_handles_missing_user_profiles_gracefully(self):
        """Test handles case where user profile is not found."""
        mock_supabase = Mock()

        # Mock project_members query
        mock_execute = Mock()
        mock_execute.data = [
            {
                "user_id": "user-1",
                "role": "admin",
                "created_at": "2026-04-01T10:00:00Z",
            }
        ]

        mock_order = Mock()
        mock_order.execute.return_value = mock_execute

        mock_eq = Mock()
        mock_eq.order.return_value = mock_order

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        # Mock get_profiles_by_ids - returns empty list (profile not found)
        with patch(
            "app.modules.users.service.get_profiles_by_ids", return_value=[]
        ):
            result = get_project_members(mock_supabase, "project-1")

        assert len(result) == 1
        assert result[0].user_id == "user-1"
        assert result[0].role == "admin"
        assert result[0].user_email is None
        assert result[0].user_full_name is None
        assert result[0].user_avatar_url is None

    def test_orders_by_created_at_ascending(self):
        """Test results are ordered by created_at in ascending order."""
        mock_supabase = Mock()

        # Mock project_members query
        mock_execute = Mock()
        mock_execute.data = []

        mock_order = Mock()
        mock_order.execute.return_value = mock_execute

        # Track order call
        order_calls = []

        def track_order(field, desc=False):
            order_calls.append({"field": field, "desc": desc})
            return mock_order

        mock_eq = Mock()
        mock_eq.order.side_effect = track_order

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = get_project_members(mock_supabase, "project-1")

        assert len(order_calls) == 1
        assert order_calls[0]["field"] == "created_at"
        assert order_calls[0]["desc"] is False


class TestCheckUserInProject:
    """Tests for check_user_in_project helper function."""

    def test_returns_true_when_user_is_project_member(self):
        """Test returns True when user is a member of the project."""
        mock_supabase = Mock()

        # Mock query - user found in project
        mock_execute = Mock()
        mock_execute.data = [{"user_id": "user-1"}]

        mock_limit = Mock()
        mock_limit.execute.return_value = mock_execute

        mock_eq_user = Mock()
        mock_eq_user.limit.return_value = mock_limit

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_user

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = check_user_in_project(mock_supabase, "project-1", "user-1")

        assert result is True

    def test_returns_false_when_user_is_not_project_member(self):
        """Test returns False when user is not a member of the project."""
        mock_supabase = Mock()

        # Mock query - user not found in project
        mock_execute = Mock()
        mock_execute.data = []

        mock_limit = Mock()
        mock_limit.execute.return_value = mock_execute

        mock_eq_user = Mock()
        mock_eq_user.limit.return_value = mock_limit

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_user

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = check_user_in_project(mock_supabase, "project-1", "user-1")

        assert result is False

    def test_checks_any_role_not_just_admin(self):
        """Test verifies membership regardless of role (admin, member, viewer)."""
        mock_supabase = Mock()

        # Mock query - user is viewer (not admin)
        mock_execute = Mock()
        mock_execute.data = [{"user_id": "user-1"}]

        mock_limit = Mock()
        mock_limit.execute.return_value = mock_execute

        mock_eq_user = Mock()
        mock_eq_user.limit.return_value = mock_limit

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_user

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        # Should return True for any role
        result = check_user_in_project(mock_supabase, "project-1", "user-1")

        assert result is True
        # Verify role filter was NOT applied (only user_id and project_id)
        mock_select.eq.assert_called_once_with("project_id", "project-1")


class TestIsProjectAdmin:
    """Tests for is_project_admin helper function."""

    def test_returns_true_when_user_is_admin(self):
        """Test returns True when user has admin role in project."""
        mock_supabase = Mock()

        # Mock query - user is admin
        mock_execute = Mock()
        mock_execute.data = [{"role": "admin"}]

        mock_limit = Mock()
        mock_limit.execute.return_value = mock_execute

        mock_eq_role = Mock()
        mock_eq_role.limit.return_value = mock_limit

        mock_eq_user = Mock()
        mock_eq_user.eq.return_value = mock_eq_role

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_user

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = is_project_admin(mock_supabase, "project-1", "user-1")

        assert result is True

    def test_returns_false_when_user_is_member_not_admin(self):
        """Test returns False when user is member but not admin."""
        mock_supabase = Mock()

        # Mock query - no admin role found
        mock_execute = Mock()
        mock_execute.data = []

        mock_limit = Mock()
        mock_limit.execute.return_value = mock_execute

        mock_eq_role = Mock()
        mock_eq_role.limit.return_value = mock_limit

        mock_eq_user = Mock()
        mock_eq_user.eq.return_value = mock_eq_role

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_user

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = is_project_admin(mock_supabase, "project-1", "user-1")

        assert result is False

    def test_returns_false_when_user_not_in_project(self):
        """Test returns False when user is not in project at all."""
        mock_supabase = Mock()

        # Mock query - user not found
        mock_execute = Mock()
        mock_execute.data = []

        mock_limit = Mock()
        mock_limit.execute.return_value = mock_execute

        mock_eq_role = Mock()
        mock_eq_role.limit.return_value = mock_limit

        mock_eq_user = Mock()
        mock_eq_user.eq.return_value = mock_eq_role

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_user

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = is_project_admin(mock_supabase, "project-1", "user-1")

        assert result is False

    def test_filters_specifically_for_admin_role(self):
        """Test verifies that query filters for admin role specifically."""
        mock_supabase = Mock()

        # Mock query
        mock_execute = Mock()
        mock_execute.data = []

        mock_limit = Mock()
        mock_limit.execute.return_value = mock_execute

        # Track eq calls to verify role filter
        eq_calls = []

        def track_eq(field, value):
            eq_calls.append({"field": field, "value": value})
            if field == "role":
                return mock_eq_role
            elif field == "user_id":
                return mock_eq_user
            elif field == "project_id":
                return mock_eq_project
            return Mock()

        mock_eq_role = Mock()
        mock_eq_role.limit.return_value = mock_limit

        mock_eq_user = Mock()
        mock_eq_user.eq.side_effect = track_eq

        mock_eq_project = Mock()
        mock_eq_project.eq.side_effect = track_eq

        mock_select = Mock()
        mock_select.eq.side_effect = track_eq

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = is_project_admin(mock_supabase, "project-1", "user-1")

        # Verify role filter was applied
        role_filter = [c for c in eq_calls if c["field"] == "role"]
        assert len(role_filter) == 1
        assert role_filter[0]["value"] == "admin"


class TestCountProjectAdmins:
    """Tests for count_project_admins helper function."""

    def test_returns_zero_when_no_admins(self):
        """Test returns 0 when project has no admins."""
        mock_supabase = Mock()

        # Mock query - no admins
        mock_execute = Mock()
        mock_execute.count = 0

        mock_eq_role = Mock()
        mock_eq_role.execute.return_value = mock_execute

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_role

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = count_project_admins(mock_supabase, "project-1")

        assert result == 0

    def test_returns_correct_count_of_admins(self):
        """Test returns accurate count of project admins."""
        mock_supabase = Mock()

        # Mock query - 3 admins
        mock_execute = Mock()
        mock_execute.count = 3

        mock_eq_role = Mock()
        mock_eq_role.execute.return_value = mock_execute

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_role

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = count_project_admins(mock_supabase, "project-1")

        assert result == 3

    def test_uses_exact_count(self):
        """Test uses exact count parameter in query."""
        mock_supabase = Mock()

        # Mock query
        mock_execute = Mock()
        mock_execute.count = 2

        mock_eq_role = Mock()
        mock_eq_role.execute.return_value = mock_execute

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_role

        # Track select call to verify count parameter
        select_calls = []

        def track_select(*args, **kwargs):
            select_calls.append({"args": args, "kwargs": kwargs})
            return mock_select

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.side_effect = track_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = count_project_admins(mock_supabase, "project-1")

        # Verify select was called with count="exact"
        assert len(select_calls) == 1
        assert select_calls[0]["kwargs"].get("count") == "exact"

    def test_handles_none_count_gracefully(self):
        """Test handles case where count is None."""
        mock_supabase = Mock()

        # Mock query - count is None
        mock_execute = Mock()
        mock_execute.count = None

        mock_eq_role = Mock()
        mock_eq_role.execute.return_value = mock_execute

        mock_eq_project = Mock()
        mock_eq_project.eq.return_value = mock_eq_role

        mock_select = Mock()
        mock_select.eq.return_value = mock_eq_project

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = count_project_admins(mock_supabase, "project-1")

        assert result == 0

    def test_only_counts_admin_role(self):
        """Test filters specifically for admin role, not other roles."""
        mock_supabase = Mock()

        # Mock query
        mock_execute = Mock()
        mock_execute.count = 1

        # Track eq calls
        eq_calls = []

        def track_eq(field, value):
            eq_calls.append({"field": field, "value": value})
            if field == "role":
                return mock_eq_role
            elif field == "project_id":
                return mock_eq_project
            return Mock()

        mock_eq_role = Mock()
        mock_eq_role.execute.return_value = mock_execute

        mock_eq_project = Mock()
        mock_eq_project.eq.side_effect = track_eq

        mock_select = Mock()
        mock_select.eq.side_effect = track_eq

        mock_table = Mock()
        mock_table.select.return_value = mock_select

        mock_schema = Mock()
        mock_schema.table.return_value = mock_table

        mock_supabase.schema.return_value = mock_schema

        result = count_project_admins(mock_supabase, "project-1")

        # Verify both project_id and role=admin filters were applied
        project_filter = [c for c in eq_calls if c["field"] == "project_id"]
        role_filter = [c for c in eq_calls if c["field"] == "role"]

        assert len(project_filter) == 1
        assert project_filter[0]["value"] == "project-1"
        assert len(role_filter) == 1
        assert role_filter[0]["value"] == "admin"
