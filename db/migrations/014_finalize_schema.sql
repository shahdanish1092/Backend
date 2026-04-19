-- Migration: finalize schema columns and seed HR workflow
BEGIN;

ALTER TABLE workflows
    ADD COLUMN IF NOT EXISTS n8n_webhook_url VARCHAR(500),
    ADD COLUMN IF NOT EXISTS default_params JSONB DEFAULT '{}';

ALTER TABLE execution_logs
    ADD COLUMN IF NOT EXISTS error_message TEXT;

INSERT INTO workflows (name, n8n_id, n8n_webhook_url, domain, status, active)
VALUES (
  'HR Recruitment Executor',
  'V1v6fXo7jskZjvif',
  'https://n8n-production-8c140.up.railway.app/webhook/execute-workflow',
  'hr',
  'active',
  true
) ON CONFLICT (n8n_id) DO UPDATE SET 
    name = EXCLUDED.name,
    n8n_webhook_url = EXCLUDED.n8n_webhook_url,
    domain = EXCLUDED.domain,
    status = EXCLUDED.status,
    active = EXCLUDED.active;

COMMIT;
