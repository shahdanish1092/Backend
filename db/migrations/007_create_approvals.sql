BEGIN;
CREATE TABLE IF NOT EXISTS approvals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  module TEXT NOT NULL,
  reference_id UUID,
  title TEXT NOT NULL,
  description TEXT,
  payload JSONB,
  status TEXT NOT NULL DEFAULT 'pending',
  approval_token UUID DEFAULT gen_random_uuid(),
  approved_by TEXT,
  approved_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_approvals_user_email ON approvals(user_email);
CREATE INDEX IF NOT EXISTS idx_approvals_token ON approvals(approval_token);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
COMMIT;
