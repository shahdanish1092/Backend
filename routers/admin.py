import os
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Header

import httpx

from database import get_db_connection
from orchestration import build_n8n_api_headers


router = APIRouter()


@router.get("/vendors/ping")
async def vendors_ping():
    return {"ok": True, "module": "admin.vendors"}


DOMAIN_MAP = {
  'hr': 'hr',
  'recruit': 'hr',
  'invoice': 'invoice',
  'finance': 'invoice',
  'meeting': 'meeting',
  'summar': 'meeting',
  'approval': 'approval',
}

def _map_workflow_name_to_domain(name: str) -> str:
    n = (name or "").lower()
    for key, domain in DOMAIN_MAP.items():
        if key in n:
            return domain
    return "general"

@router.post("/sync-workflows")
async def sync_workflows(x_admin_key: str | None = Header(None)):
    """Admin endpoint: fetch workflows from n8n and upsert into `workflows` table.

    Requires environment variable `ADMIN_SECRET_KEY` to be set and match `X-Admin-Key` header.
    """
    admin_key = os.getenv("ADMIN_SECRET_KEY")
    if not admin_key:
        raise HTTPException(status_code=500, detail="Server misconfigured: ADMIN_SECRET_KEY not set")
    if x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    n8n_base = os.getenv("N8N_BASE_URL", "https://n8n-production-b3aa.up.railway.app").rstrip('/')
    
    url = f"{n8n_base}/api/v1/workflows"
    headers = build_n8n_api_headers()
    headers.setdefault("ngrok-skip-browser-warning", "true")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch workflows from n8n: {exc}") from exc

    workflows_data = payload.get("data") if isinstance(payload, dict) and "data" in payload else (payload if isinstance(payload, list) else [])
    if workflows_data is None:
        workflows_data = []

    conn = get_db_connection()
    count = 0
    synced_workflows = []
    
    try:
        with conn.cursor() as cur:
            for item in workflows_data:
                n8n_id = item.get("id") or item.get("uuid") or item.get("workflowId")
                if not n8n_id:
                    continue
                name = item.get("name") or ""
                active = bool(item.get("active", False))
                is_archived = bool(item.get("isArchived", item.get("is_archived", False)))
                domain = _map_workflow_name_to_domain(name)
                raw = json.dumps(item, default=str)
                
                # Fetch detailed workflow to get webhook path
                webhook_url = None
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        detail_resp = await client.get(f"{url}/{n8n_id}", headers=headers)
                        if detail_resp.status_code == 200:
                            detailed_wf = detail_resp.json()
                            nodes = detailed_wf.get("nodes", [])
                            for node in nodes:
                                if node.get("type", "").endswith("webhook"):
                                    path = node.get("parameters", {}).get("path")
                                    if path:
                                        webhook_url = f"{n8n_base}/webhook/{path}"
                                        break
                except Exception:
                    pass

                cur.execute(
                    """
                    INSERT INTO workflows (n8n_id, name, domain, active, is_archived, raw, status, n8n_webhook_url, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (n8n_id) DO UPDATE SET
                      name = EXCLUDED.name,
                      domain = EXCLUDED.domain,
                      active = EXCLUDED.active,
                      is_archived = EXCLUDED.is_archived,
                      raw = EXCLUDED.raw,
                      n8n_webhook_url = EXCLUDED.n8n_webhook_url,
                      status = EXCLUDED.status,
                      updated_at = now()
                    RETURNING id
                    """,
                    (n8n_id, name, domain, active, is_archived, raw, "active" if active else "inactive", webhook_url),
                )
                _ = cur.fetchone()
                count += 1
                synced_workflows.append({
                    "name": name,
                    "domain": domain,
                    "id": n8n_id
                })
        conn.commit()
    finally:
        conn.close()

    return {"synced": count, "workflows": synced_workflows}
