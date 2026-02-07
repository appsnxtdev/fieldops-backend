-- Master materials (org-level catalog) and link from project materials. Run after 008.

CREATE TABLE IF NOT EXISTS fieldops.master_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL CHECK (unit IN (
        'kg', 'L', 'pieces', 'm', 'm²', 'bags', 'tonnes', 'cubic m', 'boxes', 'rolls'
    )),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_master_materials_tenant_id ON fieldops.master_materials(tenant_id);

ALTER TABLE fieldops.master_materials ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role master_materials" ON fieldops.master_materials FOR ALL USING (true) WITH CHECK (true);

-- Allow only fixed units for project materials; backfill existing invalid units to 'pieces'
UPDATE fieldops.materials
SET unit = 'pieces'
WHERE unit IS NULL OR unit NOT IN (
    'kg', 'L', 'pieces', 'm', 'm²', 'bags', 'tonnes', 'cubic m', 'boxes', 'rolls'
);

ALTER TABLE fieldops.materials
    ADD COLUMN IF NOT EXISTS master_material_id UUID REFERENCES fieldops.master_materials(id) ON DELETE SET NULL,
    ADD CONSTRAINT chk_materials_unit CHECK (unit IN (
        'kg', 'L', 'pieces', 'm', 'm²', 'bags', 'tonnes', 'cubic m', 'boxes', 'rolls'
    ));

CREATE INDEX IF NOT EXISTS idx_materials_master_material_id ON fieldops.materials(master_material_id);
