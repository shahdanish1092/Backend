# Deployment Checklist

## Railway Environment Variables (Backend Service)

Set these in: Railway → worthy-manifestation → Backend → Variables

| Variable | Value | Required |
|----------|-------|----------|
| DATABASE_URL | `postgresql://postgres:UeQPgBPldwyXoAjyEySkyYKEvXdOglxo@metro.proxy.rlwy.net:48417/railway` | YES |
| N8N_BASE_URL | `https://n8n-production-b3aa.up.railway.app` | YES |
| N8N_API_KEY | *(from n8n Settings → API)* | YES |
| N8N_WEBHOOK_BASE_URL | `https://n8n-production-b3aa.up.railway.app` | YES |
| N8N_WEBHOOK_PATH | `execute-workflow` | YES |
| BACKEND_PUBLIC_URL | `https://backend-production-8d62.up.railway.app` | YES |
| N8N_CALLBACK_SECRET | `sb1ifQs7dOoMfUc5HX394lBStsKWMmG2B3aDr4Is4_I` | YES |

## Railway Environment Variables (n8n Service)

Set these in: Railway → overflowing-clarity → n8n → Variables

| Variable | Value | Required |
|----------|-------|----------|
| N8N_CALLBACK_SECRET | `sb1ifQs7dOoMfUc5HX394lBStsKWMmG2B3aDr4Is4_I` | YES |
| WEBHOOK_URL | `https://n8n-production-b3aa.up.railway.app` | YES |

> **IMPORTANT**: `N8N_CALLBACK_SECRET` must be IDENTICAL on both the backend and n8n services.
> With the v3 workflow update, n8n no longer reads `$env` variables inside workflow expressions.
> Instead, the backend injects `backend_base_url` and `n8n_callback_secret` in the trigger payload.

## Pre-Deploy Steps
1. Ensure env vars listed above are set in both projects.
2. Run migrations: `railway run python scripts/run_migrations.py` (or run locally with `DATABASE_URL` set).
3. Push to `main` (Railway auto-deploys).

## Post-Deploy Verification
1. Health check: `curl https://backend-production-8d62.up.railway.app/health` → expect `{"status":"ok"}`
2. n8n ping: `curl https://backend-production-8d62.up.railway.app/api/n8n/ping` → expect `{"status":"ok",...}`
3. Manual webhook test:
   ```bash
   curl -X POST https://n8n-production-b3aa.up.railway.app/webhook/execute-workflow \
     -H "Content-Type: application/json" \
     -d '{"request_id":"manual-1","text":"hello"}'
   ```
   Expect: 200 `{"message":"Workflow was started"}`
4. Run E2E (only after migrations and envs set):
   ```bash
   BACKEND_PUBLIC_URL=https://backend-production-8d62.up.railway.app \
   N8N_WEBHOOK_BASE_URL=https://n8n-production-b3aa.up.railway.app \
   N8N_WEBHOOK_PATH=execute-workflow \
   N8N_CALLBACK_SECRET=sb1ifQs7dOoMfUc5HX394lBStsKWMmG2B3aDr4Is4_I \
   DATABASE_URL=postgresql://postgres:UeQPgBPldwyXoAjyEySkyYKEvXdOglxo@metro.proxy.rlwy.net:48417/railway \
   RUN_E2E=1 python -m pytest tests/e2e_workflow_test.py -q -s
   ```

## Notes
- Do NOT hardcode secrets or production URLs in source files; use env vars.
- Ensure `N8N_WEBHOOK_PATH` is the exact webhook path configured in your workflow's Webhook trigger node.
- Keep `N8N_CALLBACK_SECRET` identical between the backend and n8n environment variables.
- The v3 workflow no longer uses `$env` expressions; all config is injected via the trigger payload.
