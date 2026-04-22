import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.modules.notifications.service import create_notification


@pytest.mark.asyncio
async def test_create_notification_inserts_record():
    """Test that create_notification inserts a notification record."""
    mock_supabase = Mock()
    mock_table = Mock()
    mock_insert = Mock()
    mock_execute = Mock()

    # Setup mock chain
    mock_supabase.schema.return_value.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert
    mock_insert.execute.return_value.data = [{
        'id': 'notif-123',
        'tenant_id': 'tenant-1',
        'user_id': 'user-2',
        'actor_id': 'user-1',
        'type': 'task_assigned',
        'title': 'New Task Assigned',
        'message': 'John assigned you a task',
        'entity_type': 'task',
        'entity_id': 'task-1',
        'project_id': 'proj-1',
        'metadata': {'actor_name': 'John'},
        'is_read': False,
        'created_at': '2026-04-10T10:00:00Z',
        'read_at': None
    }]

    with patch('app.modules.notifications.service.send_fcm_push', new_callable=AsyncMock):
        result = await create_notification(
            supabase=mock_supabase,
            tenant_id='tenant-1',
            user_id='user-2',
            actor_id='user-1',
            type='task_assigned',
            title='New Task Assigned',
            message='John assigned you a task',
            entity_type='task',
            entity_id='task-1',
            project_id='proj-1',
            metadata={'actor_name': 'John'}
        )

    assert result['id'] == 'notif-123'
    assert result['type'] == 'task_assigned'
    mock_table.insert.assert_called_once()
