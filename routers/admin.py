import os
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Header
import httpx

from database import get_db_connection
from orchestration import build_n8n_api_headers

router = APIRouter()
logger = logging.getLogger(__name__)

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
    """
    admin_key = os.getenv("ADMIN_SECRET_KEY")
    if not admin_key:
        raise HTTPException(status_code=500, detail="Server misconfigured: ADMIN_SECRET_KEY not set")
    if x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    n8n_base = os.getenv("N8N_BASE_URL", "").rstrip('/')
    if not n8n_base:
         raise HTTPException(status_code=500, detail="N8N_BASE_URL not configured")
    
    url = f"{n8n_base}/api/v1/workflows"
    headers = build_n8n_api_headers()
    headers.setdefault("ngrok-skip-browser-warning", "true")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"n8n API returned {resp.status_code}: {resp.text}")
            payload = resp.json()
        except Exception as exc:
            if isinstance(exc, HTTPException): raise
            raise HTTPException(status_code=502, detail=f"Failed to fetch workflows from n8n: {exc}") from exc

        workflows_data = payload.get("data", []) if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])
        
        conn = get_db_connection()
        count = 0
        synced_workflows = []
        
        try:
            with conn.cursor() as cur:
                for item in workflows_data:
                    n8n_id = item.get("id") or item.get("uuid") or item.get("workflowId")
                    if not n8n_id:
                        continue
                    
                    name = item.get("name") or "Untitled Workflow"
                    active = bool(item.get("active", False))
                    is_archived = bool(item.get("isArchived", False))
                    domain = _map_workflow_name_to_domain(name)
                    
                    # Fetch detailed workflow for webhook path
                    webhook_url = None
                    try:
                        detail_resp = await client.get(f"{url}/{n8n_id}", headers=headers)
                        if detail_resp.status_code == 200:
                            detailed_wf = detail_resp.json()
                            nodes = detailed_wf.get("nodes", [])
                            for node in nodes:
                                if node.get("type", "").lower().endswith("webhook"):
                                    path = node.get("parameters", {}).get("path")
                                    if path:
                                        webhook_url = f"{n8n_base}/webhook/{path}"
                                        break
                    except Exception as e:
                        logger.warning(f"Failed to fetch details for workflow {n8n_id}: {e}")

                    cur.execute(
                        """
                        INSERT INTO workflows (n8n_id, name, domain, active, is_archived, raw, status, n8n_webhook_url, updated_at)
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
                        """,
                        (n8n_id, name, domain, active, is_archived, json.dumps(item), "active" if active else "inactive", webhook_url),
                    )
                    count += 1
                    synced_workflows.append({"name": name, "domain": domain, "id": n8n_id})
            conn.commit()
        except Exception as e:
            logger.exception("Database error during workflow sync")
            raise HTTPException(status_code=500, detail=f"Database sync failed: {e}")
        finally:
            conn.close()

    return {"synced": count, "workflows": synced_workflows}
