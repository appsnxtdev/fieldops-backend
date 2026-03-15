-- Labour types (org-level) and daily labour headcount per site. Run after 014.

CREATE TABLE IF NOT EXISTS fieldops.labour_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    rate_per_day NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (rate_per_day >= 0),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_labour_types_tenant_id ON fieldops.labour_types(tenant_id);

CREATE TABLE IF NOT EXISTS fieldops.labour_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    labour_type_id UUID NOT NULL REFERENCES fieldops.labour_types(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    count INTEGER NOT NULL DEFAULT 0 CHECK (count >= 0),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (project_id, date, labour_type_id)
);

CREATE INDEX IF NOT EXISTS idx_labour_daily_project_date ON fieldops.labour_daily(project_id, date);
CREATE INDEX IF NOT EXISTS idx_labour_daily_type ON fieldops.labour_daily(labour_type_id);

ALTER TABLE fieldops.labour_types ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role labour_types" ON fieldops.labour_types FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE fieldops.labour_daily ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role labour_daily" ON fieldops.labour_daily FOR ALL USING (true) WITH CHECK (true);
