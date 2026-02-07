-- Projects (tenant_id, no org FK) and project_members. Run after 003.
CREATE TABLE IF NOT EXISTS fieldops.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_tenant_id ON fieldops.projects(tenant_id);

CREATE TABLE IF NOT EXISTS fieldops.project_members (
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_project_members_project_id ON fieldops.project_members(project_id);
CREATE INDEX IF NOT EXISTS idx_project_members_user_id ON fieldops.project_members(user_id);

ALTER TABLE fieldops.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE fieldops.project_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access projects"
    ON fieldops.projects FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access project_members"
    ON fieldops.project_members FOR ALL USING (true) WITH CHECK (true);
