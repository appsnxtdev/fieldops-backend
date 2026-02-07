-- Tenant membership: tenant_id from JWT (no FK). Run after 001, 002.
CREATE TABLE IF NOT EXISTS fieldops.tenant_members (
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('org_admin', 'member')),
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_members_tenant_id ON fieldops.tenant_members(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_members_user_id ON fieldops.tenant_members(user_id);

ALTER TABLE fieldops.tenant_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access tenant_members"
    ON fieldops.tenant_members FOR ALL
    USING (true)
    WITH CHECK (true);
