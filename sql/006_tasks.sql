-- Task statuses (per project) and tasks. Single assignee, custom statuses.
CREATE TABLE IF NOT EXISTS fieldops.project_task_statuses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_statuses_project ON fieldops.project_task_statuses(project_id);

CREATE TABLE IF NOT EXISTS fieldops.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status_id UUID REFERENCES fieldops.project_task_statuses(id) ON DELETE SET NULL,
    assignee_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    due_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tasks_project ON fieldops.tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON fieldops.tasks(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON fieldops.tasks(status_id);

ALTER TABLE fieldops.project_task_statuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE fieldops.tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role task_statuses" ON fieldops.project_task_statuses FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role tasks" ON fieldops.tasks FOR ALL USING (true) WITH CHECK (true);
