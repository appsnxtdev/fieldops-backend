-- Notifications table for task-related notifications
CREATE TABLE IF NOT EXISTS fieldops.notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  actor_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('task_assigned', 'task_status_changed', 'task_comment_added')),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'task',
  entity_id UUID NOT NULL,
  project_id UUID REFERENCES fieldops.projects(id) ON DELETE CASCADE,
  metadata JSONB,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  read_at TIMESTAMP WITH TIME ZONE
);

-- Performance indexes
CREATE INDEX idx_notifications_user_created ON fieldops.notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_tenant_user ON fieldops.notifications(tenant_id, user_id);
CREATE INDEX idx_notifications_cleanup ON fieldops.notifications(created_at);

-- Row-Level Security
ALTER TABLE fieldops.notifications ENABLE ROW LEVEL SECURITY;

-- Users can only read their own notifications
CREATE POLICY notifications_select_own ON fieldops.notifications
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can only update their own notifications (for marking as read)
CREATE POLICY notifications_update_own ON fieldops.notifications
  FOR UPDATE
  USING (auth.uid() = user_id);

COMMENT ON TABLE fieldops.notifications IS 'Stores user notifications for task events';
COMMENT ON COLUMN fieldops.notifications.type IS 'Type: task_assigned, task_status_changed, task_comment_added';
COMMENT ON COLUMN fieldops.notifications.entity_type IS 'Entity type, currently only task';
COMMENT ON COLUMN fieldops.notifications.is_read IS 'Whether notification has been read by user';
COMMENT ON COLUMN fieldops.notifications.metadata IS 'JSON: actor_name, task_title, old_status, new_status, etc.';

-- User devices table for FCM tokens
CREATE TABLE IF NOT EXISTS fieldops.user_devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  fcm_token TEXT NOT NULL,
  platform TEXT NOT NULL CHECK (platform IN ('android', 'ios')),
  device_id TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, fcm_token)
);

CREATE INDEX idx_user_devices_user ON fieldops.user_devices(user_id);
CREATE INDEX idx_user_devices_token ON fieldops.user_devices(fcm_token);

-- RLS
ALTER TABLE fieldops.user_devices ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_devices_own ON fieldops.user_devices
  FOR ALL
  USING (auth.uid() = user_id);

COMMENT ON TABLE fieldops.user_devices IS 'Stores FCM tokens for push notifications';

-- Cleanup function for old notifications (30 days)
CREATE OR REPLACE FUNCTION fieldops.cleanup_old_notifications()
RETURNS void AS $$
BEGIN
  DELETE FROM fieldops.notifications
  WHERE created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION fieldops.cleanup_old_notifications IS 'Deletes notifications older than 30 days';

-- Schedule with pg_cron (runs daily at 2 AM UTC)
-- Note: Ensure pg_cron extension is enabled first
-- SELECT cron.schedule('cleanup-notifications', '0 2 * * *', 'SELECT fieldops.cleanup_old_notifications()');
