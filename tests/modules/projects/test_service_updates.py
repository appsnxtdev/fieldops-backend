"""Tests for project updates CRUD operations in service layer."""

import pytest
from unittest.mock import Mock, patch
from app.modules.projects.service import list_project_updates, add_project_update
from app.modules.projects.schemas import ProjectResponse


def test_list_project_updates_returns_empty_list_when_no_updates():
    """Test list_project_updates returns empty list when no updates exist."""
    mock_supabase = Mock()

    # Mock the query chain for project_updates
    mock_execute = Mock()
    mock_execute.data = []

    mock_order = Mock()
    mock_order.execute.return_value = mock_execute

    mock_eq_tenant = Mock()
    mock_eq_tenant.order.return_value = mock_order

    mock_eq_project = Mock()
    mock_eq_project.eq.return_value = mock_eq_tenant

    mock_select = Mock()
    mock_select.eq.return_value = mock_eq_project

    mock_table = Mock()
    mock_table.select.return_value = mock_select

    mock_schema = Mock()
    mock_schema.table.return_value = mock_table

    mock_supabase.schema.return_value = mock_schema

    result = list_project_updates(mock_supabase, "project-1", "tenant-1")

    assert result == []
    mock_schema.table.assert_called_with("project_updates")


def test_list_project_updates_returns_updates_with_author_info():
    """Test list_project_updates returns updates with populated author info."""
    mock_supabase = Mock()

    # Mock data returned from database
    mock_data = [
        {
            "id": "update-1",
            "project_id": "project-1",
            "author_id": "user-1",
            "note": "First update",
            "created_at": "2026-04-01T10:00:00Z",
            "profiles": {
                "id": "user-1",
                "email": "user1@example.com",
                "full_name": "John Doe",
            },
        },
        {
            "id": "update-2",
            "project_id": "project-1",
            "author_id": "user-2",
            "note": "Second update",
            "created_at": "2026-04-02T11:00:00Z",
            "profiles": {
                "id": "user-2",
                "email": "user2@example.com",
                "full_name": "Jane Smith",
            },
        },
    ]

    # Mock the query chain
    mock_execute = Mock()
    mock_execute.data = mock_data

    mock_order = Mock()
    mock_order.execute.return_value = mock_execute

    mock_eq_tenant = Mock()
    mock_eq_tenant.order.return_value = mock_order

    mock_eq_project = Mock()
    mock_eq_project.eq.return_value = mock_eq_tenant

    mock_select = Mock()
    mock_select.eq.return_value = mock_eq_project

    mock_table = Mock()
    mock_table.select.return_value = mock_select

    mock_schema = Mock()
    mock_schema.table.return_value = mock_table

    mock_supabase.schema.return_value = mock_schema

    result = list_project_updates(mock_supabase, "project-1", "tenant-1")

    assert len(result) == 2
    assert result[0].id == "update-1"
    assert result[0].note == "First update"
    assert result[0].author.id == "user-1"
    assert result[0].author.email == "user1@example.com"
    assert result[0].author.full_name == "John Doe"

    assert result[1].id == "update-2"
    assert result[1].author.full_name == "Jane Smith"


def test_list_project_updates_enforces_tenant_isolation():
    """Test list_project_updates only returns updates for projects in user's tenant."""
    mock_supabase = Mock()

    # Mock empty result (tenant isolation blocks access)
    mock_execute = Mock()
    mock_execute.data = []

    mock_order = Mock()
    mock_order.execute.return_value = mock_execute

    mock_eq_tenant = Mock()
    mock_eq_tenant.order.return_value = mock_order

    mock_eq_project = Mock()
    mock_eq_project.eq.return_value = mock_eq_tenant

    mock_select = Mock()
    mock_select.eq.return_value = mock_eq_project

    mock_table = Mock()
    mock_table.select.return_value = mock_select

    mock_schema = Mock()
    mock_schema.table.return_value = mock_table

    mock_supabase.schema.return_value = mock_schema

    # User from different tenant tries to access project
    result = list_project_updates(mock_supabase, "project-other-tenant", "tenant-1")

    assert result == []


def test_add_project_update_creates_update_and_returns_with_author():
    """Test add_project_update creates update and returns it with author info."""
    mock_supabase = Mock()

    # Mock project exists
    mock_project = ProjectResponse(
        id="project-1",
        tenant_id="tenant-1",
        name="Test Project",
        timezone="Asia/Kolkata",
    )

    # Mock insert update
    mock_insert_data = {
        "id": "update-1",
        "project_id": "project-1",
        "author_id": "user-1",
        "note": "Test note",
        "created_at": "2026-04-15T10:00:00Z",
        "profiles": {
            "id": "user-1",
            "email": "test@example.com",
            "full_name": "Test User",
        },
    }
    mock_insert_execute = Mock()
    mock_insert_execute.data = [mock_insert_data]

    mock_insert_select = Mock()
    mock_insert_select.execute.return_value = mock_insert_execute

    mock_insert = Mock()
    mock_insert.select.return_value = mock_insert_select

    # Mock update last_activity_at
    mock_update_execute = Mock()
    mock_update_execute.data = [{"id": "project-1"}]

    mock_update_eq_tenant = Mock()
    mock_update_eq_tenant.execute.return_value = mock_update_execute

    mock_update_eq_id = Mock()
    mock_update_eq_id.eq.return_value = mock_update_eq_tenant

    mock_update = Mock()
    mock_update.eq.return_value = mock_update_eq_id

    # Setup table mocking
    def table_side_effect(name):
        if name == "projects":
            mock_table = Mock()
            mock_table.update.return_value = mock_update
            return mock_table
        elif name == "project_updates":
            mock_table = Mock()
            mock_table.insert.return_value = mock_insert
            return mock_table
        return Mock()

    mock_schema = Mock()
    mock_schema.table.side_effect = table_side_effect

    mock_supabase.schema.return_value = mock_schema

    with patch("app.modules.projects.service.get_project", return_value=mock_project):
        result = add_project_update(mock_supabase, "project-1", "user-1", "tenant-1", "Test note")

    assert result.id == "update-1"
    assert result.note == "Test note"
    assert result.author.id == "user-1"
    assert result.author.email == "test@example.com"
    assert result.author.full_name == "Test User"


def test_add_project_update_enforces_tenant_isolation():
    """Test add_project_update raises error when user tries to add update to project in different tenant."""
    mock_supabase = Mock()

    # Mock project not found (tenant isolation)
    with patch("app.modules.projects.service.get_project", return_value=None):
        with pytest.raises(ValueError, match="Project not found or access denied"):
            add_project_update(mock_supabase, "project-other-tenant", "user-1", "tenant-1", "Unauthorized note")


def test_add_project_update_updates_last_activity_at():
    """Test add_project_update updates project's last_activity_at timestamp."""
    mock_supabase = Mock()

    # Mock project exists
    mock_project = ProjectResponse(
        id="project-1",
        tenant_id="tenant-1",
        name="Test Project",
        timezone="Asia/Kolkata",
    )

    # Mock insert update
    mock_insert_data = {
        "id": "update-1",
        "project_id": "project-1",
        "author_id": "user-1",
        "note": "Test note",
        "created_at": "2026-04-15T10:00:00Z",
        "profiles": {
            "id": "user-1",
            "email": "test@example.com",
            "full_name": "Test User",
        },
    }
    mock_insert_execute = Mock()
    mock_insert_execute.data = [mock_insert_data]

    mock_insert_select = Mock()
    mock_insert_select.execute.return_value = mock_insert_execute

    mock_insert = Mock()
    mock_insert.select.return_value = mock_insert_select

    # Mock update last_activity_at
    mock_update_execute = Mock()
    mock_update_execute.data = [{"id": "project-1"}]

    mock_update_eq_tenant = Mock()
    mock_update_eq_tenant.execute.return_value = mock_update_execute

    mock_update_eq_id = Mock()
    mock_update_eq_id.eq.return_value = mock_update_eq_tenant

    mock_update = Mock()
    mock_update.eq.return_value = mock_update_eq_id

    # Track update calls
    update_calls = []

    def track_update(data):
        update_calls.append(data)
        return mock_update

    # Setup table mocking
    def table_side_effect(name):
        if name == "projects":
            mock_table = Mock()
            mock_table.update.side_effect = track_update
            return mock_table
        elif name == "project_updates":
            mock_table = Mock()
            mock_table.insert.return_value = mock_insert
            return mock_table
        return Mock()

    mock_schema = Mock()
    mock_schema.table.side_effect = table_side_effect

    mock_supabase.schema.return_value = mock_schema

    with patch("app.modules.projects.service.get_project", return_value=mock_project):
        result = add_project_update(mock_supabase, "project-1", "user-1", "tenant-1", "Test note")

    # Verify last_activity_at was updated
    assert len(update_calls) == 1
    assert "last_activity_at" in update_calls[0]
    # Verify the timestamp is recent (within last minute)
    from datetime import datetime, timezone, timedelta
    last_activity = datetime.fromisoformat(update_calls[0]["last_activity_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    assert (now - last_activity) < timedelta(minutes=1)


def test_add_project_update_validates_empty_note():
    """Test add_project_update raises error for empty or whitespace-only notes."""
    mock_supabase = Mock()

    # Test empty string
    with pytest.raises(ValueError, match="Note cannot be empty"):
        add_project_update(mock_supabase, "project-1", "user-1", "tenant-1", "")

    # Test whitespace-only string
    with pytest.raises(ValueError, match="Note cannot be empty"):
        add_project_update(mock_supabase, "project-1", "user-1", "tenant-1", "   ")

    # Test string with only newlines and spaces
    with pytest.raises(ValueError, match="Note cannot be empty"):
        add_project_update(mock_supabase, "project-1", "user-1", "tenant-1", "\n\t  \n")
