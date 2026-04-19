import os
import uuid
import json
import httpx
from fastapi import APIRouter, HTTPException, Body
from typing import Optional

from database import get_db_connection
from orchestration import build_n8n_webhook_headers

router = APIRouter()

@router.get("/meetings/ping")
async def meetings_ping():
    return {"ok": True, "module": "meetings"}

@router.post("/webhooks/meeting")
async def trigger_meeting_webhook(
    user_email: str = Body(...),
    type: str = Body(...),
    content: str = Body(...),
    title: str = Body(...),
    attendees: list = Body(default=[])
):
    if not user_email or not content:
        raise HTTPException(status_code=400, detail="Missing user_email or content")
        
    execution_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        # Create execution log
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO execution_logs (id, user_email, module, status, input_payload, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, now(), now())
                """,
                (execution_id, user_email, 'meeting', 'pending', json.dumps({"title": title, "type": type}))
            )
            
            # Fetch workflow webhook
            cur.execute("SELECT n8n_webhook_url FROM workflows WHERE domain = 'meeting' AND status = 'active' LIMIT 1")
            wf_row = cur.fetchone()
            if not wf_row or not wf_row[0]:
                raise HTTPException(status_code=500, detail="Meeting workflow not configured in database")
            n8n_webhook_url = wf_row[0]

        conn.commit()

        # Build payload
        backend_public = (os.getenv("BACKEND_PUBLIC_URL") or os.getenv("FASTAPI_BASE_URL") or "http://localhost:8000").rstrip("/")
        webhook_payload = {
            "request_id": execution_id,
            "workflow_type": "meeting",
            "callback_url": f"{backend_public}/api/execution-callback",
            "backend_base_url": backend_public,
            "n8n_callback_secret": os.getenv("N8N_CALLBACK_SECRET", ""),
            "payload": {
                "user_email": user_email,
                "type": type,
                "content": content,
                "title": title,
                "attendees": attendees
            }
        }

        headers = build_n8n_webhook_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(n8n_webhook_url, json=webhook_payload, headers=headers)
            resp.raise_for_status()

        # Update status
        with conn.cursor() as cur:
            cur.execute("UPDATE execution_logs SET status = 'running', updated_at = now() WHERE id = %s", (execution_id,))
        conn.commit()

        return {"execution_id": execution_id, "status": "processing", "message": "Meeting transcript/audio uploaded. Processing started."}
        
    except httpx.HTTPStatusError as e:
        with conn.cursor() as cur:
            cur.execute("UPDATE execution_logs SET status = 'failed', error_message = %s, updated_at = now() WHERE id = %s", (str(e), execution_id))
        conn.commit()
        raise HTTPException(status_code=502, detail=f"n8n webhook failed: {e}")
    finally:
        conn.close()

@router.get("/meetings/{user_email}")
async def get_meetings(user_email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, status, created_at, result_payload, error_message
                FROM execution_logs 
                WHERE user_email = %s AND module = 'meeting'
                ORDER BY created_at DESC 
                LIMIT 50
                """,
                (user_email,)
            )
            rows = cur.fetchall()
            
        results = []
        for r in rows:
            exec_id, status, created_at, result_payload, error_message = r
            
            # Map the result payload safely
            rp = result_payload if isinstance(result_payload, dict) else {}
            summary = rp.get("summary", {})
            if isinstance(summary, str):
                try: summary = json.loads(summary)
                except Exception: summary = {}
            
            results.append({
                "id": exec_id,
                "status": status,
                "created_at": created_at.isoformat() if created_at else None,
                "error_message": error_message,
                "title": rp.get("title", "Unknown Meeting"),
                "transcript_length": rp.get("transcript_length", 0),
                "executive_summary": summary.get("executive_summary", ""),
                "key_decisions": summary.get("key_decisions", []),
                "action_items": summary.get("action_items", []),
                "sentiment": summary.get("sentiment", "neutral")
            })
            
        return {"meetings": results}
    finally:
        conn.close()
