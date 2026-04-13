BEGIN;

ALTER TABLE execution_logs
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

UPDATE execution_logs
SET updated_at = COALESCE(updated_at, created_at, now())
WHERE updated_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_execution_logs_status ON execution_logs (status);

COMMIT;
