-- Materials (per project, fixed unit) and ledger (in/out).
CREATE TABLE IF NOT EXISTS fieldops.materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_materials_project ON fieldops.materials(project_id);

CREATE TABLE IF NOT EXISTS fieldops.material_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id UUID NOT NULL REFERENCES fieldops.materials(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('in', 'out')),
    quantity DECIMAL NOT NULL CHECK (quantity > 0),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_material_ledger_material ON fieldops.material_ledger(material_id);

ALTER TABLE fieldops.materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE fieldops.material_ledger ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role materials" ON fieldops.materials FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role material_ledger" ON fieldops.material_ledger FOR ALL USING (true) WITH CHECK (true);
