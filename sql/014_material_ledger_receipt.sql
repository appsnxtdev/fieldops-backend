-- Optional receipt for material ledger (inflow). Run after 008/013.
-- Create Storage bucket "material_receipts" in Supabase Dashboard if using receipt uploads.
ALTER TABLE fieldops.material_ledger
    ADD COLUMN IF NOT EXISTS receipt_path TEXT;
