import os
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Header
import httpx

from auth.guards import require_user_header
from database import get_db_connection
from orchestration import build_n8n_api_headers

router = APIRouter()

CONNECTOR_TYPES = ["gmail", "google_drive", "google_calendar", "google_sheets", "hr_system"]


@router.get("")
async def list_connectors(user_email: str | None = None, x_user_email: str | None = Header(None)):
    """Return available connector types and whether connected for a user."""
    conn = get_db_connection()
    try:
        user_email = require_user_header(conn, x_user_email, claimed_user_email=user_email, require_known_user=False)

        # Check Google tokens
        with conn.cursor() as cur:
            cur.execute(
                "SELECT scopes, created_at FROM google_tokens WHERE user_email = %s",
                (user_email,),
            )
            google_row = cur.fetchone()
        
        has_google = bool(google_row)
        
        # Check other connectors
        with conn.cursor() as cur:
            cur.execute(
                "SELECT connector_type, connected, metadata FROM connectors WHERE user_email = %s",
                (user_email,),
            )
            rows = cur.fetchall()
        
        by_type = {r[0]: {"connected": r[1], "metadata": r[2]} for r in rows}
        
        results = []
        for c in CONNECTOR_TYPES:
            if c.startswith("google_") or c == "gmail":
                connected = has_google
                metadata = {"connected_at": google_row[1].isoformat()} if google_row else None
            else:
                info = by_type.get(c, {"connected": False, "metadata": None})
                connected = bool(info.get("connected"))
                metadata = info.get("metadata")
                
            results.append({
                "connector": c,
                "connected": connected,
                "metadata": metadata
            })
            
        return {"connectors": results}
    finally:
        conn.close()


@router.post("/{connector_type}/connect")
async def connect_connector(connector_type: str, user_email: str, x_user_email: str | None = Header(None)):
    """Initiate connect flow for a connector.

    For `gmail` this returns the backend Google OAuth redirect URL (uses existing /api/auth/google).
    For other connectors currently returns instructions (or could be extended to trigger n8n credential creation).
    """
    connector_type = (connector_type or "").lower()
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail="Unknown connector type")

    conn = get_db_connection()
    try:
        require_user_header(conn, x_user_email, claimed_user_email=user_email, require_known_user=False)
    finally:
        conn.close()

    if connector_type == "gmail":
        frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
        # Redirect to backend auth endpoint which starts Google OAuth.
        return {"redirect": f"/api/auth/google?next={frontend}"}

    # For non-Google connectors, return a helpful message. In future we can call n8n credential APIs.
    return {"message": f"Connector {connector_type} connect flow must be configured. Configure credentials in n8n and then save a reference via DELETE/POST endpoints."}


@router.delete("/{connector_type}")
async def delete_connector(connector_type: str, user_email: str, x_user_email: str | None = Header(None)):
    connector_type = (connector_type or "").lower()
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail="Unknown connector type")

    conn = get_db_connection()
    try:
        user_email = require_user_header(conn, x_user_email, claimed_user_email=user_email, require_known_user=False)

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, n8n_credential_id FROM connectors WHERE user_email = %s AND connector_type = %s",
                (user_email, connector_type),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Connector not found")
            rec_id, n8n_cred = row[0], row[1]

            # If n8n_cred is present, attempt to delete it from n8n
            if n8n_cred:
                n8n_base = os.getenv("N8N_BASE_URL")
                if n8n_base:
                    url = f"{n8n_base.rstrip('/')}/api/v1/credentials/{n8n_cred}"
                    headers = build_n8n_api_headers()
                    headers.setdefault("ngrok-skip-browser-warning", "true")
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            resp = await client.delete(url, headers=headers)
                            resp.raise_for_status()
                    except Exception:
                        # non-fatal; continue to remove local record
                        pass

            # remove local record
            cur.execute("DELETE FROM connectors WHERE id = %s", (rec_id,))
        conn.commit()
    finally:
        conn.close()
    return {"deleted": True}
