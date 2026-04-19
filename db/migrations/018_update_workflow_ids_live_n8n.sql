-- Align workflows.n8n_id with live n8n (Invoice Processor id drift)
BEGIN;

UPDATE workflows
SET n8n_id = '7GVaSgIqOVLT0vs5',
    name = 'Invoice Processor',
    n8n_webhook_url = 'https://n8n-production-8c140.up.railway.app/webhook/invoice-webhook-v2',
    updated_at = now()
WHERE domain = 'invoice';

UPDATE workflows
SET n8n_webhook_url = 'https://n8n-production-8c140.up.railway.app/webhook/execute-workflow',
    updated_at = now()
WHERE domain = 'hr';

COMMIT;
