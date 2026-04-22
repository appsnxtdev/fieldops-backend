"""Tests for project updates and status API routes."""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from app.modules.projects.schemas import (
    ProjectResponse,
    ProjectUpdateNoteResponse,
    UserBasicInfo,
)


class TestListProjectUpdatesRoute:
    """Test GET /projects/{project_id}/updates endpoint."""

    @patch("app.modules.projects.routes.get_project_access")
    @patch("app.modules.projects.routes.list_project_updates")
    def test_list_updates_success(self, mock_list_updates, mock_get_access):
        """Test successfully listing project updates."""
        from app.modules.projects.routes import list_project_updates_route

        # Mock access control
        mock_get_access.return_value = lambda: {"tenant_id": "tenant-1", "role": "viewer"}

        # Mock service response
        mock_updates = [
            ProjectUpdateNoteResponse(
                id="update-1",
                project_id="project-1",
                author_id="user-1",
                author=UserBasicInfo(id="user-1", email="user1@example.com", full_name="John Doe"),
                note="First update",
                created_at="2026-04-01T10:00:00Z",
            ),
            ProjectUpdateNoteResponse(
                id="update-2",
                project_id="project-1",
                author_id="user-2",
                author=UserBasicInfo(id="user-2", email="user2@example.com", full_name="Jane Smith"),
                note="Second update",
                created_at="2026-04-02T11:00:00Z",
            ),
        ]
        mock_list_updates.return_value = mock_updates

        mock_supabase = Mock()

        result = list_project_updates_route(
            project_id="project-1",
            access={"tenant_id": "tenant-1", "role": "viewer"},
            supabase=mock_supabase,
        )

        assert len(result) == 2
        assert result[0].id == "update-1"
        assert result[0].note == "First update"
        assert result[1].id == "update-2"
        mock_list_updates.assert_called_once_with(mock_supabase, "project-1", "tenant-1")

    @patch("app.modules.projects.routes.get_project_access")
    @patch("app.modules.projects.routes.list_project_updates")
    def test_list_updates_empty_list(self, mock_list_updates, mock_get_access):
        """Test listing updates returns empty list when no updates exist."""
        from app.modules.projects.routes import list_project_updates_route

        # Mock access control
        mock_get_access.return_value = lambda: {"tenant_id": "tenant-1", "role": "viewer"}

        # Mock empty service response
        mock_list_updates.return_value = []

        mock_supabase = Mock()

        result = list_project_updates_route(
            project_id="project-1",
            access={"tenant_id": "tenant-1", "role": "viewer"},
            supabase=mock_supabase,
        )

        assert result == []
        mock_list_updates.assert_called_once_with(mock_supabase, "project-1", "tenant-1")


class TestAddProjectUpdateRoute:
    """Test POST /projects/{project_id}/updates endpoint."""

    @patch("app.modules.projects.routes.get_project_access")
    @patch("app.modules.projects.routes.add_project_update")
    @patch("app.modules.projects.routes.get_current_user")
    def test_add_update_success(self, mock_get_user, mock_add_update, mock_get_access):
        """Test successfully adding a project update."""
        from app.modules.projects.routes import add_project_update_route
        from app.modules.projects.schemas import ProjectUpdateNoteCreate

        # Mock access control
        mock_get_access.return_value = lambda: {"tenant_id": "tenant-1", "role": "viewer"}

        # Mock current user
        mock_get_user.return_value = lambda: {"id": "user-1"}

        # Mock service response
        mock_response = ProjectUpdateNoteResponse(
            id="update-1",
            project_id="project-1",
            author_id="user-1",
            author=UserBasicInfo(id="user-1", email="test@example.com", full_name="Test User"),
            note="New update",
            created_at="2026-04-15T10:00:00Z",
        )
        mock_add_update.return_value = mock_response

        mock_supabase = Mock()
        payload = ProjectUpdateNoteCreate(note="New update")

        result = add_project_update_route(
            project_id="project-1",
            payload=payload,
            access={"tenant_id": "tenant-1", "role": "viewer"},
            current_user={"id": "user-1"},
            supabase=mock_supabase,
        )

        assert result.id == "update-1"
        assert result.note == "New update"
        assert result.author.id == "user-1"
        mock_add_update.assert_called_once_with(
            mock_supabase,
            "project-1",
            "user-1",
            "tenant-1",
            "New update",
        )

    @patch("app.modules.projects.routes.get_project_access")
    @patch("app.modules.projects.routes.add_project_update")
    @patch("app.modules.projects.routes.get_current_user")
    def test_add_update_validates_empty_note(self, mock_get_user, mock_add_update, mock_get_access):
        """Test adding update with empty note raises HTTPException with 400 status."""
        from app.modules.projects.routes import add_project_update_route
        from app.modules.projects.schemas import ProjectUpdateNoteCreate

        # Mock access control
        mock_get_access.return_value = lambda: {"tenant_id": "tenant-1", "role": "admin"}

        # Mock current user
        mock_get_user.return_value = lambda: {"id": "user-1"}

        # Mock service to raise ValueError for empty note
        mock_add_update.side_effect = ValueError("Note cannot be empty")

        mock_supabase = Mock()
        payload = ProjectUpdateNoteCreate(note="")

        with pytest.raises(HTTPException) as exc_info:
            add_project_update_route(
                project_id="project-1",
                payload=payload,
                access={"tenant_id": "tenant-1", "role": "admin"},
                current_user={"id": "user-1"},
                supabase=mock_supabase,
            )

        assert exc_info.value.status_code == 400
        assert "Note cannot be empty" in exc_info.value.detail

    @patch("app.modules.projects.routes.get_project_access")
    @patch("app.modules.projects.routes.add_project_update")
    @patch("app.modules.projects.routes.get_current_user")
    def test_add_update_project_not_found(self, mock_get_user, mock_add_update, mock_get_access):
        """Test adding update to non-existent project raises HTTPException with 404 status."""
        from app.modules.projects.routes import add_project_update_route
        from app.modules.projects.schemas import ProjectUpdateNoteCreate

        # Mock access control
        mock_get_access.return_value = lambda: {"tenant_id": "tenant-1", "role": "admin"}

        # Mock current user
        mock_get_user.return_value = lambda: {"id": "user-1"}

        # Mock service to raise ValueError for project not found
        mock_add_update.side_effect = ValueError("Project not found or access denied")

        mock_supabase = Mock()
        payload = ProjectUpdateNoteCreate(note="Test note")

        with pytest.raises(HTTPException) as exc_info:
            add_project_update_route(
                project_id="non-existent",
                payload=payload,
                access={"tenant_id": "tenant-1", "role": "admin"},
                current_user={"id": "user-1"},
                supabase=mock_supabase,
            )

        assert exc_info.value.status_code == 404
        assert "Project not found" in exc_info.value.detail


class TestUpdateProjectStatusRoute:
    """Test PATCH /projects/{project_id}/status endpoint."""

    @patch("app.modules.projects.routes.get_project_access")
    @patch("app.modules.projects.routes.get_project")
    @patch("app.modules.projects.routes.cache_delete")
    def test_update_status_success(self, mock_cache_delete, mock_get_project, mock_get_access):
        """Test successfully updating project status."""
        from app.modules.projects.routes import update_project_status_route
        from app.modules.projects.schemas import ProjectStatusUpdateRequest

        # Mock access control
        mock_get_access.return_value = lambda: {"tenant_id": "tenant-1", "role": "admin"}

        # Mock re-fetch after update
        mock_refetched = ProjectResponse(
            id="project-1",
            tenant_id="tenant-1",
            name="Test Project",
            timezone="Asia/Kolkata",
            status="active",
            last_activity_at="2026-04-15T10:00:00Z",
        )
        mock_get_project.return_value = mock_refetched

        # Mock supabase for direct update
        mock_execute = Mock()
        mock_eq_tenant = Mock()
        mock_eq_tenant.execute.return_value = mock_execute
        mock_eq_id = Mock()
        mock_eq_id.eq.return_value = mock_eq_tenant
        mock_update = Mock()
        mock_update.eq.return_value = mock_eq_id
        mock_table = Mock()
        mock_table.update.return_value = mock_update
        mock_schema = Mock()
        mock_schema.table.return_value = mock_table
        mock_supabase = Mock()
        mock_supabase.schema.return_value = mock_schema

        mock_redis = Mock()

        payload = ProjectStatusUpdateRequest(status="active")

        result = update_project_status_route(
            project_id="project-1",
            payload=payload,
            access={"tenant_id": "tenant-1", "role": "admin"},
            supabase=mock_supabase,
            redis=mock_redis,
        )

        assert result.id == "project-1"
        assert result.status == "active"
        assert result.last_activity_at == "2026-04-15T10:00:00Z"

        # Verify cache was cleared
        mock_cache_delete.assert_called_once()

        # Verify direct update was called with both status and last_activity_at
        mock_table.update.assert_called_once()
        update_data = mock_table.update.call_args[0][0]
        assert "status" in update_data
        assert update_data["status"] == "active"
        assert "last_activity_at" in update_data

        # Verify project was re-fetched
        mock_get_project.assert_called_once_with(mock_supabase, "project-1", "tenant-1")

    @patch("app.modules.projects.routes.get_project_access")
    @patch("app.modules.projects.routes.get_project")
    @patch("app.modules.projects.routes.cache_delete")
    def test_update_status_project_not_found_after_update(
        self, mock_cache_delete, mock_get_project, mock_get_access
    ):
        """Test update status raises 404 if project not found after update."""
        from app.modules.projects.routes import update_project_status_route
        from app.modules.projects.schemas import ProjectStatusUpdateRequest

        # Mock access control
        mock_get_access.return_value = lambda: {"tenant_id": "tenant-1", "role": "admin"}

        # Mock re-fetch returns None
        mock_get_project.return_value = None

        # Mock supabase for direct update
        mock_execute = Mock()
        mock_eq_tenant = Mock()
        mock_eq_tenant.execute.return_value = mock_execute
        mock_eq_id = Mock()
        mock_eq_id.eq.return_value = mock_eq_tenant
        mock_update = Mock()
        mock_update.eq.return_value = mock_eq_id
        mock_table = Mock()
        mock_table.update.return_value = mock_update
        mock_schema = Mock()
        mock_schema.table.return_value = mock_table
        mock_supabase = Mock()
        mock_supabase.schema.return_value = mock_schema

        mock_redis = Mock()

        payload = ProjectStatusUpdateRequest(status="active")

        with pytest.raises(HTTPException) as exc_info:
            update_project_status_route(
                project_id="project-1",
                payload=payload,
                access={"tenant_id": "tenant-1", "role": "admin"},
                supabase=mock_supabase,
                redis=mock_redis,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Project not found"

    @patch("app.modules.projects.routes.get_project_access")
    def test_update_status_validates_status_value(self, mock_get_access):
        """Test update status validates status is a valid enum value."""
        from app.modules.projects.schemas import ProjectStatusUpdateRequest
        from pydantic import ValidationError

        # This test verifies the Pydantic schema validation
        # Invalid status should be rejected at schema level
        with pytest.raises(ValidationError):
            ProjectStatusUpdateRequest(status="invalid_status")

        # Valid status should pass
        valid_request = ProjectStatusUpdateRequest(status="planning")
        assert valid_request.status == "planning"
