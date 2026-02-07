-- Add location, address, project_admin_user_id to projects. Run after 010.
ALTER TABLE fieldops.projects
    ADD COLUMN IF NOT EXISTS location TEXT,
    ADD COLUMN IF NOT EXISTS address TEXT,
    ADD COLUMN IF NOT EXISTS project_admin_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_projects_project_admin_user_id ON fieldops.projects(project_admin_user_id);