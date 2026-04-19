-- Migration: seed invoice and meeting workflows
BEGIN;

INSERT INTO workflows (name, n8n_id, n8n_webhook_url, domain, status, active)
VALUES 
  (
    'Invoice Processor',
    '7GVaSgIqOVLT0vs5',
    'https://n8n-production-8c140.up.railway.app/webhook/invoice-webhook-v2',
    'invoice',
    'active',
    true
  ),
  (
    'Meeting Summarizer',
    'IKw6v1FpCLV3zni5',
    'https://n8n-production-8c140.up.railway.app/webhook/meeting-webhook-v2',
    'meeting',
    'active',
    true
  )
ON CONFLICT (n8n_id) DO UPDATE SET
  name = EXCLUDED.name,
  n8n_webhook_url = EXCLUDED.n8n_webhook_url,
  domain = EXCLUDED.domain,
  status = EXCLUDED.status,
  active = EXCLUDED.active;

COMMIT;