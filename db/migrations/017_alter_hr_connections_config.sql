-- HR connect flow: store format, secret, and configured flag
BEGIN;

ALTER TABLE hr_connections
  ADD COLUMN IF NOT EXISTS input_format TEXT,
  ADD COLUMN IF NOT EXISTS secret TEXT,
  ADD COLUMN IF NOT EXISTS webhook_configured BOOLEAN DEFAULT false;

COMMIT;
