-- Migration: add screening_criteria JSONB to hr_connections
BEGIN;

ALTER TABLE hr_connections
  ADD COLUMN IF NOT EXISTS screening_criteria JSONB DEFAULT '{}'::jsonb;

COMMIT;
