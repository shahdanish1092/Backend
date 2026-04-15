-- Migration: create workflows table
BEGIN;

CREATE TABLE IF NOT EXISTS workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  n8n_id TEXT NOT NULL,
  name TEXT,
  domain TEXT,
  active BOOLEAN DEFAULT TRUE,
  is_archived BOOLEAN DEFAULT FALSE,
  raw JSONB,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workflows_n8n_id ON workflows(n8n_id);
CREATE INDEX IF NOT EXISTS idx_workflows_domain ON workflows(domain);
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);

COMMIT;
