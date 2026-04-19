-- Seed standard workflow records

INSERT INTO workflows (name, n8n_id, n8n_webhook_url, domain, status)
VALUES 
  (
    'HR Recruitment Executor',
    'V1v6fXo7jskZjvif',
    'https://n8n-production-8c140.up.railway.app/webhook/execute-workflow',
    'hr',
    'active'
  ),
  (
    'Invoice Processor',
    'uZLgL9y2HZtyKdjM',
    'https://n8n-production-8c140.up.railway.app/webhook/invoice-webhook-v2',
    'invoice',
    'active'
  ),
  (
    'Meeting Summarizer',
    'IKw6v1FpCLV3zni5',
    'https://n8n-production-8c140.up.railway.app/webhook/meeting-webhook-v2',
    'meeting',
    'active'
  )
ON CONFLICT (n8n_id) DO UPDATE SET
  n8n_webhook_url = EXCLUDED.n8n_webhook_url,
  status = EXCLUDED.status,
  name = EXCLUDED.name,
  domain = EXCLUDED.domain;
