BEGIN;
CREATE TABLE IF NOT EXISTS hr_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
  n8n_workflow_id TEXT,
  webhook_url TEXT,
  is_active BOOLEAN DEFAULT true,
  last_sync TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_hr_user ON hr_connections(user_email);
COMMIT;
