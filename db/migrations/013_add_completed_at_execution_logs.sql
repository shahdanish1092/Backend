-- Migration: add completed_at to execution_logs
BEGIN;

ALTER TABLE execution_logs
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

COMMIT;
