-- Project lifecycle management migration
-- Adds workflow status, dates, owner, and project updates table

-- Add lifecycle fields to projects table
ALTER TABLE fieldops.projects
  ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'planning' CHECK (status IN ('planning', 'active', 'on_hold', 'completed', 'archived')),
  ADD COLUMN IF NOT EXISTS project_owner_id UUID REFERENCES auth.users(id),
  ADD COLUMN IF NOT EXISTS start_date DATE,
  ADD COLUMN IF NOT EXISTS end_date DATE,
  ADD COLUMN IF NOT EXISTS estimated_completion_date DATE,
  ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_status ON fieldops.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON fieldops.projects(project_owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_tenant_status ON fieldops.projects(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_projects_last_activity ON fieldops.projects(last_activity_at DESC);

-- Create project_updates table (activity feed)
CREATE TABLE IF NOT EXISTS fieldops.project_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_project_updates_project ON fieldops.project_updates(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_project_updates_author ON fieldops.project_updates(author_id);

-- Enable RLS
ALTER TABLE fieldops.project_updates ENABLE ROW LEVEL SECURITY;

-- RLS policies
CREATE POLICY "Service role full access project_updates"
    ON fieldops.project_updates FOR ALL USING (true) WITH CHECK (true);

-- RLS policy for authenticated users (tenant-scoped)
CREATE POLICY "Users can view project_updates in their tenant projects"
    ON fieldops.project_updates FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM fieldops.projects p
            WHERE p.id = project_updates.project_id
            AND p.tenant_id IN (
                SELECT tenant_id FROM fieldops.tenant_members
                WHERE user_id = auth.uid()
            )
        )
    );

CREATE POLICY "Users can insert project_updates in their tenant projects"
    ON fieldops.project_updates FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM fieldops.projects p
            WHERE p.id = project_updates.project_id
            AND p.tenant_id IN (
                SELECT tenant_id FROM fieldops.tenant_members
                WHERE user_id = auth.uid()
            )
        )
    );

-- Grant permissions
GRANT ALL ON fieldops.project_updates TO anon, authenticated, service_role;

-- Backfill existing projects with default status
UPDATE fieldops.projects SET status = 'planning' WHERE status IS NULL;
