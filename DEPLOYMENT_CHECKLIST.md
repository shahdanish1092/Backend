# Deployment Checklist

## Railway Environment Variables (Backend Service)

Set these in: Railway → worthy-manifestation → Backend → Variables

| Variable | Value | Required |
|----------|-------|----------|
| DATABASE_URL | (auto-set by Railway Postgres) | YES |
| N8N_BASE_URL | https://your-n8n-instance.railway.app | YES |
| N8N_API_KEY | (from n8n Settings → API) | YES |
| N8N_WEBHOOK_BASE_URL | https://your-n8n-instance.railway.app | YES |
| N8N_WEBHOOK_PATH | execute-workflow-<your-workflow-id> | YES |
| BACKEND_PUBLIC_URL | https://your-backend.railway.app | YES |
| N8N_CALLBACK_SECRET | (random string, same on both) | YES |

## Railway Environment Variables (n8n Service)

Set these in: Railway → overflowing-clarity → n8n → Variables

| Variable | Value | Required |
|----------|-------|----------|
| N8N_CALLBACK_SECRET | (same as backend) | YES |
| WEBHOOK_URL | https://your-n8n-instance.railway.app | YES |

## Pre-Deploy Steps
1. Ensure env vars listed above are set in both projects.
2. Run migrations: `railway run python scripts/run_migrations.py` (or run locally with `DATABASE_URL` set).
3. Push to `main` (Railway auto-deploys).

## Post-Deploy Verification
1. Health check: `curl https://<backend>/docs` → expect 200 HTML.
2. Manual webhook test:
   ```bash
   curl -X POST https://<n8n>/webhook/<N8N_WEBHOOK_PATH> \
     -H "Content-Type: application/json" \
     -d '{"request_id":"manual-1","text":"hello"}'
   ```
   Expect: 200 {"message":"Workflow was started"}
3. Run E2E (only after migrations and envs set):
   ```bash
   BACKEND_PUBLIC_URL=https://<backend> RUN_E2E=1 python -m pytest tests/e2e_workflow_test.py -q -s
   ```

## Notes
- Do NOT hardcode secrets or production URLs in source files; use env vars.
- Ensure `N8N_WEBHOOK_PATH` is the exact webhook path configured in your workflow's Webhook trigger node.
- Keep `N8N_CALLBACK_SECRET` identical between the backend and n8n environment variables.
