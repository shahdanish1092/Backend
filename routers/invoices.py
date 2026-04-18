import os
import base64
import uuid
import json
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body, Request
from typing import Optional

from database import get_db_connection

router = APIRouter()

@router.post("/webhooks/invoice/trigger")
async def trigger_invoice_webhook(
    request: Request,
    user_email: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = Form(None)
):
    # Support both JSON and Multipart Form
    content_type = request.headers.get("content-type", "")
    file_base64 = None
    
    if "application/json" in content_type:
        payload = await request.json()
        user_email = payload.get("user_email")
        file_base64 = payload.get("file_base64")
        filename = payload.get("filename")
    else:
        if file:
            file_bytes = await file.read()
            file_base64 = base64.b64encode(file_bytes).decode('utf-8')
            filename = filename or file.filename
        else:
            # Check if it's passed as form fields but no actual file object
            pass

    if not user_email or not file_base64:
        raise HTTPException(status_code=400, detail="Missing user_email or file_base64")

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
                (execution_id, user_email, 'invoice', 'pending', json.dumps({"filename": filename}))
            )
            
            # Fetch workflow webhook
            cur.execute("SELECT n8n_webhook_url FROM workflows WHERE domain = 'invoice' AND status = 'active' LIMIT 1")
            wf_row = cur.fetchone()
            if not wf_row or not wf_row[0]:
                raise HTTPException(status_code=500, detail="Invoice workflow not configured in database")
            n8n_webhook_url = wf_row[0]

            # Fetch google token if available
            cur.execute("SELECT access_token FROM google_tokens WHERE user_email = %s", (user_email,))
            tok_row = cur.fetchone()
            google_token = tok_row[0] if tok_row else ""
            
        conn.commit()

        # Build payload
        backend_public = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
        webhook_payload = {
            "request_id": execution_id,
            "workflow_type": "invoice",
            "callback_url": f"{backend_public.rstrip('/')}/api/execution-callback",
            "backend_base_url": backend_public,
            "n8n_callback_secret": os.getenv("N8N_CALLBACK_SECRET", ""),
            "payload": {
                "user_email": user_email,
                "file_base64": file_base64,
                "filename": filename,
                "google_access_token": google_token
            }
        }

        # POST to webhook (using Basic Auth to secure the endpoint just in case)
        auth_user = os.getenv("N8N_BASIC_AUTH_USER", "")
        auth_pass = os.getenv("N8N_BASIC_AUTH_PASSWORD", "")
        basic_auth_b64 = base64.b64encode(f"{auth_user}:{auth_pass}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {basic_auth_b64}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(n8n_webhook_url, json=webhook_payload, headers=headers)
            resp.raise_for_status()

        # Update status
        with conn.cursor() as cur:
            cur.execute("UPDATE execution_logs SET status = 'running', updated_at = now() WHERE id = %s", (execution_id,))
        conn.commit()

        return {"execution_id": execution_id, "status": "processing", "message": "Invoice uploaded. Processing started."}
        
    except httpx.HTTPStatusError as e:
        with conn.cursor() as cur:
            cur.execute("UPDATE execution_logs SET status = 'failed', error_message = %s, updated_at = now() WHERE id = %s", (str(e), execution_id))
        conn.commit()
        raise HTTPException(status_code=502, detail=f"n8n webhook failed: {e}")
    finally:
        conn.close()

@router.get("/invoices/{user_email}")
async def get_invoices(user_email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, status, created_at, result_payload, error_message
                FROM execution_logs 
                WHERE user_email = %s AND module = 'invoice'
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
            
            results.append({
                "id": exec_id,
                "status": status,
                "created_at": created_at.isoformat() if created_at else None,
                "error_message": error_message,
                "vendor_name": rp.get("vendor_name", "Unknown"),
                "invoice_number": rp.get("invoice_number", ""),
                "total_amount": rp.get("total_amount", 0.0),
                "invoice_date": rp.get("invoice_date", ""),
                "confidence_score": rp.get("confidence_score", 0.0)
            })
            
        return {"invoices": results}
    finally:
        conn.close()
