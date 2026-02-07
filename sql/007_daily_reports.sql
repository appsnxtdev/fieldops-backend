-- Daily reports: one per user per project per day. Entries = append-only log (photo or note).
CREATE TABLE IF NOT EXISTS fieldops.daily_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (project_id, user_id, report_date)
);

CREATE TABLE IF NOT EXISTS fieldops.daily_report_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    daily_report_id UUID NOT NULL REFERENCES fieldops.daily_reports(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('photo', 'note')),
    content TEXT NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_daily_reports_project_date ON fieldops.daily_reports(project_id, report_date);
CREATE INDEX IF NOT EXISTS idx_daily_report_entries_report ON fieldops.daily_report_entries(daily_report_id);

ALTER TABLE fieldops.daily_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE fieldops.daily_report_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role daily_reports" ON fieldops.daily_reports FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role daily_report_entries" ON fieldops.daily_report_entries FOR ALL USING (true) WITH CHECK (true);
