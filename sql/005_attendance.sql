-- Attendance: check-in/check-out with selfie and lat/lng. Date in project TZ.
CREATE TABLE IF NOT EXISTS fieldops.attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    check_in_at TIMESTAMPTZ,
    check_out_at TIMESTAMPTZ,
    check_in_selfie_path TEXT,
    check_out_selfie_path TEXT,
    check_in_lat DOUBLE PRECISION,
    check_in_lng DOUBLE PRECISION,
    check_out_lat DOUBLE PRECISION,
    check_out_lng DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (project_id, user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_attendance_project_date ON fieldops.attendance(project_id, date);
CREATE INDEX IF NOT EXISTS idx_attendance_user_id ON fieldops.attendance(user_id);

ALTER TABLE fieldops.attendance ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access attendance"
    ON fieldops.attendance FOR ALL USING (true) WITH CHECK (true);
