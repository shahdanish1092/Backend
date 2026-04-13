from fastapi import APIRouter, HTTPException
import os
import httpx

router = APIRouter()


@router.post("/webhooks/invoice/trigger")
async def trigger_invoice_webhook(payload: dict):
    """Trigger an n8n webhook for invoice processing. This only forwards the payload to the configured n8n endpoint."""
    n8n_base = os.getenv("N8N_BASE_URL")
    if not n8n_base:
        raise HTTPException(status_code=500, detail="n8n base url not configured")

    webhook_url = f"{n8n_base}/webhook/invoice"
    async with httpx.AsyncClient() as client:
        resp = await client.post(webhook_url, json=payload, timeout=10.0)
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="n8n webhook failed")
    return {"status": "triggered"}
