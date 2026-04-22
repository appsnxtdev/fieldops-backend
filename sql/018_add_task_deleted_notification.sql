-- Add task_deleted to notification types
ALTER TABLE fieldops.notifications
  DROP CONSTRAINT IF EXISTS notifications_type_check;

ALTER TABLE fieldops.notifications
  ADD CONSTRAINT notifications_type_check
  CHECK (type IN ('task_assigned', 'task_status_changed', 'task_comment_added', 'task_deleted'));

COMMENT ON COLUMN fieldops.notifications.type IS 'Type: task_assigned, task_status_changed, task_comment_added, task_deleted';
