-- Add start_date and planned_completion_date to projects table
-- Required for dashboard status calculations (on_track, at_risk, delayed)

ALTER TABLE fieldops.projects
  ADD COLUMN IF NOT EXISTS start_date DATE,
  ADD COLUMN IF NOT EXISTS planned_completion_date DATE;

-- Add index for date queries
CREATE INDEX IF NOT EXISTS idx_projects_completion_date
  ON fieldops.projects(planned_completion_date)
  WHERE planned_completion_date IS NOT NULL;

COMMENT ON COLUMN fieldops.projects.start_date IS 'Project start date for timeline calculations';
COMMENT ON COLUMN fieldops.projects.planned_completion_date IS 'Target completion date for status calculations';
