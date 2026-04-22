-- Backfill project_members from existing data
-- Run after 022_profiles_tenant_visibility.sql

DO $$
DECLARE
    admin_count INT := 0;
    member_count INT := 0;
BEGIN
    -- Insert admins from projects.project_admin_user_id
    INSERT INTO fieldops.project_members (project_id, user_id, role)
    SELECT
        p.id AS project_id,
        p.project_admin_user_id AS user_id,
        'admin' AS role
    FROM fieldops.projects p
    WHERE p.project_admin_user_id IS NOT NULL
    ON CONFLICT (project_id, user_id) DO NOTHING;

    GET DIAGNOSTICS admin_count = ROW_COUNT;
    RAISE NOTICE 'Inserted % project admins', admin_count;

    -- Insert members from users with task assignments
    -- Users who have been assigned tasks become members (if not already admin or member)
    INSERT INTO fieldops.project_members (project_id, user_id, role)
    SELECT DISTINCT
        t.project_id,
        t.assignee_id AS user_id,
        'member' AS role
    FROM fieldops.tasks t
    WHERE t.assignee_id IS NOT NULL
    ON CONFLICT (project_id, user_id) DO NOTHING;

    GET DIAGNOSTICS member_count = ROW_COUNT;
    RAISE NOTICE 'Inserted % project members from task assignments', member_count;

    RAISE NOTICE 'Backfill complete: % admins, % members', admin_count, member_count;
END $$;

-- Create index on role column for performance
CREATE INDEX IF NOT EXISTS idx_project_members_role ON fieldops.project_members(role);
