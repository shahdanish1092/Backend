BEGIN;
CREATE TABLE IF NOT EXISTS vendors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  name TEXT NOT NULL,
  email TEXT,
  approved BOOLEAN DEFAULT false,
  invoice_count INTEGER DEFAULT 0,
  total_spend NUMERIC(14,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vendors_user_email ON vendors(user_email);
COMMIT;
