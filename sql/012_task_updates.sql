-- Task update notes (activity log): assignee/team can add notes per task, viewable as a log.
CREATE TABLE IF NOT EXISTS fieldops.task_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES fieldops.tasks(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_updates_task ON fieldops.task_updates(task_id);
CREATE INDEX IF NOT EXISTS idx_task_updates_created ON fieldops.task_updates(created_at DESC);

ALTER TABLE fieldops.task_updates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role task_updates" ON fieldops.task_updates FOR ALL USING (true) WITH CHECK (true);

GRANT ALL ON fieldops.task_updates TO anon, authenticated, service_role;
