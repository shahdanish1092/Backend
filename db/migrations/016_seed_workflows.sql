-- Seed standard workflow records

INSERT INTO workflows (name, n8n_id, n8n_webhook_url, domain, status)
VALUES 
  (
    'HR Recruitment Executor',
    'cUNV8MuHEZMQpn4U',
    'https://n8n-production-b3aa.up.railway.app/webhook/execute-workflow',
    'hr',
    'active'
  ),
  (
    'Invoice Processor',
    'INVOICE_WORKFLOW_ID',
    'https://n8n-production-b3aa.up.railway.app/webhook/invoice-process',
    'invoice',
    'active'
  ),
  (
    'Meeting Summarizer',
    'MEETING_WORKFLOW_ID',
    'https://n8n-production-b3aa.up.railway.app/webhook/meeting-summarize',
    'meeting',
    'active'
  )
ON CONFLICT (n8n_id) DO UPDATE SET
  n8n_webhook_url = EXCLUDED.n8n_webhook_url,
  status = EXCLUDED.status,
  name = EXCLUDED.name,
  domain = EXCLUDED.domain;
