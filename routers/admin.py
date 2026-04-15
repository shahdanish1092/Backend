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


def _map_workflow_name_to_domain(name: str) -> str:
    n = (name or "").lower()
    if "hr" in n or "recruit" in n or "candidate" in n:
        return "hr"
    if "invoice" in n or "billing" in n or "invoice" in n:
        return "invoices"
    if "meeting" in n or "calendar" in n or "summar" in n:
        return "meetings"
    if "approval" in n or "approve" in n or "sign" in n:
        return "approvals"
    return "general"


@router.post("/sync-workflows")
async def sync_workflows(x_admin_key: str | None = Header(None)):
    """Admin endpoint: fetch workflows from n8n and upsert into `workflows` table.

    Requires environment variable `ADMIN_KEY` to be set and match `X-Admin-Key` header.
    """
    admin_key = os.getenv("ADMIN_KEY")
    if not admin_key:
        raise HTTPException(status_code=500, detail="Server misconfigured: ADMIN_KEY not set")
    if x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    n8n_base = os.getenv("N8N_BASE_URL")
    if not n8n_base:
        raise HTTPException(status_code=500, detail="N8N_BASE_URL not configured")

    url = f"{n8n_base.rstrip('/')}/api/v1/workflows"
    headers = build_n8n_api_headers()
    headers.setdefault("ngrok-skip-browser-warning", "true")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch workflows from n8n: {exc}") from exc

    workflows = payload.get("data") if isinstance(payload, dict) and "data" in payload else (payload if isinstance(payload, list) else [])
    if workflows is None:
        workflows = []

    conn = get_db_connection()
    count = 0
    try:
        with conn.cursor() as cur:
            for item in workflows:
                n8n_id = item.get("id") or item.get("uuid") or item.get("workflowId")
                if not n8n_id:
                    continue
                name = item.get("name") or ""
                active = bool(item.get("active", False))
                is_archived = bool(item.get("isArchived", item.get("is_archived", False)))
                domain = _map_workflow_name_to_domain(name)
                raw = json.dumps(item, default=str)

                cur.execute(
                    """
                    INSERT INTO workflows (n8n_id, name, domain, active, is_archived, raw, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (n8n_id) DO UPDATE SET
                      name = EXCLUDED.name,
                      domain = EXCLUDED.domain,
                      active = EXCLUDED.active,
                      is_archived = EXCLUDED.is_archived,
                      raw = EXCLUDED.raw,
                      status = EXCLUDED.status,
                      updated_at = now()
                    RETURNING id
                    """,
                    (n8n_id, name, domain, active, is_archived, raw, "active"),
                )
                _ = cur.fetchone()
                count += 1
        conn.commit()
    finally:
        conn.close()

    return {"synced": count}
