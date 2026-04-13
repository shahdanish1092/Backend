BEGIN;
CREATE TABLE IF NOT EXISTS invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  vendor_name TEXT,
  invoice_number TEXT,
  amount NUMERIC(12,2),
  invoice_date DATE,
  due_date DATE,
  line_items JSONB,
  raw_extracted JSONB,
  status TEXT NOT NULL DEFAULT 'processing',
  n8n_execution_id TEXT,
  source_email_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invoices_user_email ON invoices(user_email);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
COMMIT;
