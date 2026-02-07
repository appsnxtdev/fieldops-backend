-- Expense: credit/debit per project. Receipt required for debit.
CREATE TABLE IF NOT EXISTS fieldops.expense_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES fieldops.projects(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('credit', 'debit')),
    amount DECIMAL NOT NULL CHECK (amount > 0),
    receipt_storage_path TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    CONSTRAINT debit_requires_receipt CHECK (type != 'debit' OR receipt_storage_path IS NOT NULL AND receipt_storage_path != '')
);

CREATE INDEX IF NOT EXISTS idx_expense_project ON fieldops.expense_transactions(project_id);

ALTER TABLE fieldops.expense_transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role expense" ON fieldops.expense_transactions FOR ALL USING (true) WITH CHECK (true);
