-- Migration: create connectors table to store per-user connector credentials
BEGIN;

CREATE TABLE IF NOT EXISTS connectors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
  connector_type TEXT NOT NULL,
  n8n_credential_id TEXT,
  connected BOOLEAN DEFAULT FALSE,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_connectors_user_type ON connectors(user_email, connector_type);

COMMIT;
