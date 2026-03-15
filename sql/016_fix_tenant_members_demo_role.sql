-- Fix: update tenant_members_role_check constraint to include 'demo' role
-- The production database may have been created with an older constraint
-- that did not include 'demo', causing INSERT/UPDATE to fail.

ALTER TABLE fieldops.tenant_members
    DROP CONSTRAINT IF EXISTS tenant_members_role_check;

ALTER TABLE fieldops.tenant_members
    ADD CONSTRAINT tenant_members_role_check
    CHECK (role IN ('org_admin', 'member', 'viewer', 'demo'));
