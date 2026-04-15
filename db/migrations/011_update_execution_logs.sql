-- Migration: add workflow_id and result_payload to execution_logs
BEGIN;

ALTER TABLE execution_logs
  ADD COLUMN IF NOT EXISTS workflow_id UUID;

ALTER TABLE execution_logs
  ADD COLUMN IF NOT EXISTS result_payload JSONB;

-- Optionally, you could add a foreign key to workflows.id if desired.
-- ALTER TABLE execution_logs ADD CONSTRAINT fk_execution_workflow FOREIGN KEY (workflow_id) REFERENCES workflows(id);

COMMIT;
