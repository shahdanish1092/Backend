-- Migration: create execution_logs table
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS execution_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  module TEXT NOT NULL,
  input_payload JSONB,
  output_summary JSONB,
  status TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_execution_logs_user_email ON execution_logs (user_email);
CREATE INDEX IF NOT EXISTS idx_execution_logs_status ON execution_logs (status);

COMMIT;
