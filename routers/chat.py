import os
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Header

from database import get_db_connection
from orchestration import (
    create_execution_log,
    merge_execution_log_output_summary,
    get_execution_log,
    build_n8n_api_headers,
    trigger_n8n_workflow,
)


router = APIRouter()


def _classify_text_simple(text: str) -> dict[str, Any]:
    t = (text or "").lower()
    if any(k in t for k in ("invoice", "bill", "amount", "vendor")):
        return {"domain": "invoices", "action": "process_invoice", "parameters": {}}
    if any(k in t for k in ("resume", "candidate", "cv", "interview", "shortlist", "hire")):
        return {"domain": "hr", "action": "process_resume", "parameters": {}}
    if any(k in t for k in ("meeting", "summar", "follow[- ]?up", "calendar")):
        return {"domain": "meetings", "action": "summarize_meeting", "parameters": {}}
    if any(k in t for k in ("approve", "approval", "sign")):
        return {"domain": "approvals", "action": "route_for_approval", "parameters": {}}
    return {"domain": "general", "action": "none", "parameters": {}}


async def _classify_text(text: str) -> dict[str, Any]:
    try:
        import httpx
        import os
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            system_prompt = (
                "You are an intent classifier for an office automation system.\n"
                "Classify the user request into exactly one domain and extract parameters.\n"
                "Respond ONLY with valid JSON, no markdown, no explanation:\n"
                "{\n"
                "  'domain': one of ['hr', 'invoice', 'meeting', 'approval', 'general'],\n"
                "  'action': 'snake_case action name',\n"
                "  'parameters': {extracted key-value pairs from the user text}\n"
                "}"
            )
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                body = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text}
                    ]
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if content:
                            import re
                            if content.startswith("```"):
                                content = re.sub(r"^```(json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
                            try:
                                return json.loads(content)
                            except Exception:
                                m = re.search(r"\{.*\}", content, re.DOTALL)
                                if m:
                                    return json.loads(m.group())
            except Exception as e:
                import logging
                logging.getLogger("office_automation.chat").error(f"Groq API call failed: {e}")
    except Exception as e:
        import logging
        logging.getLogger("office_automation.chat").error(f"Failed to setup http request: {e}")

    # fallback
    return _classify_text_simple(text)


@router.post("/chat/message")
async def post_message(payload: dict):
    # required fields
    if not payload.get("text") or not isinstance(payload.get("active_connectors", []), list) or not payload.get("user_email"):
        raise HTTPException(status_code=400, detail="Missing required fields: text, active_connectors, user_email")

    text = payload.get("text")
    active_connectors = payload.get("active_connectors")
    user_email = payload.get("user_email")

    classification = await _classify_text(text)
    domain = classification.get("domain", "general")
    action = classification.get("action", "none")
    parameters = classification.get("parameters", {})

    conn = get_db_connection()
    try:
        # Step 2: find a workflow
        with conn.cursor() as cur:
            cur.execute(
                "SELECT n8n_id, name, n8n_webhook_url FROM workflows WHERE domain = %s AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
                (domain,),
            )
            wf = cur.fetchone()

        if not wf:
            return {"execution_id": None, "domain": domain, "message": "No workflow is configured for this request type.", "workflow_name": None}

        n8n_id, workflow_name, n8n_webhook_url = wf[0], wf[1], wf[2]

        # Step 3 & 4: generate execution_id and create execution log
        import uuid
        execution_id = str(uuid.uuid4())
        
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO execution_logs (id, user_email, module, status, input_payload, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, now(), now())
                """,
                (execution_id, user_email, domain, "pending", json.dumps({"text": text, "parameters": parameters, "active_connectors": active_connectors}))
            )
        conn.commit()

        # Step 5: Build payload
        backend_public = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
        built_payload = {
            "request_id": execution_id,
            "workflow_type": domain,
            "callback_url": f"{backend_public.rstrip('/')}/api/execution-callback",
            "backend_base_url": backend_public,
            "n8n_callback_secret": os.getenv("N8N_CALLBACK_SECRET", ""),
            "payload": {
                "user_email": user_email,
                **parameters
            }
        }

        # Step 6: POST to webhook
        import httpx
        import base64
        
        # Use provided URL or fallback to env variable if null
        webhook_url = n8n_webhook_url
        if not webhook_url:
            webhook_base = os.getenv("N8N_WEBHOOK_BASE_URL", os.getenv("N8N_BASE_URL", "http://localhost:5678")).rstrip("/")
            webhook_url = f"{webhook_base}/webhook/execute-workflow"
            
        auth_user = os.getenv("N8N_BASIC_AUTH_USER", "")
        auth_pass = os.getenv("N8N_BASIC_AUTH_PASSWORD", "")
        basic_auth_b64 = base64.b64encode(f"{auth_user}:{auth_pass}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {basic_auth_b64}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(webhook_url, json=built_payload, headers=headers)
                resp.raise_for_status()
                
            # Step 7: Update execution status
            with conn.cursor() as cur:
                cur.execute("UPDATE execution_logs SET status = 'running', updated_at = now() WHERE id = %s", (execution_id,))
            conn.commit()
            
        except Exception as exc:
            import logging
            logging.getLogger("office_automation.chat").error(f"Failed to trigger n8n workflow for {execution_id}: {exc}")
            with conn.cursor() as cur:
                cur.execute("UPDATE execution_logs SET status = 'failed', updated_at = now() WHERE id = %s", (execution_id,))
            conn.commit()
            return {"execution_id": execution_id, "domain": domain, "action": action, "message": "Failed to trigger workflow", "error": str(exc), "workflow_name": workflow_name}

        # Step 8: Return
        return {
            "execution_id": execution_id,
            "domain": domain,
            "action": action,
            "message": f"Workflow started. I'll update you when it completes.",
            "workflow_name": workflow_name
        }
    finally:
        conn.close()


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, x_user_email: str | None = Header(None)):
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Missing X-User-Email header")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    e.id::text, 
                    e.status, 
                    e.module as domain, 
                    e.created_at as started_at, 
                    e.completed_at, 
                    e.result_payload, 
                    e.error_message, 
                    w.name as workflow_name,
                    e.user_email
                FROM execution_logs e
                LEFT JOIN workflows w ON e.module = w.domain AND w.status = 'active'
                WHERE e.id = %s
                ORDER BY w.updated_at DESC
                LIMIT 1
                """,
                (execution_id,)
            )
            row = cur.fetchone()
            
        if not row:
            raise HTTPException(status_code=404, detail="Execution not found")
            
        if row[8] != x_user_email:
            raise HTTPException(status_code=403, detail="Forbidden")
            
        return {
            "id": row[0],
            "status": row[1],
            "domain": row[2],
            "started_at": row[3].isoformat() if row[3] else None,
            "completed_at": row[4].isoformat() if row[4] else None,
            "result_payload": row[5],
            "error_message": row[6],
            "workflow_name": row[7]
        }
    finally:
        conn.close()


@router.get("/executions")
async def list_executions(x_user_email: str | None = Header(None), status: str | None = None, limit: int = 20):
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Missing X-User-Email header")
        
    limit = min(limit, 100)
    conn = get_db_connection()
    try:
        query = """
            SELECT 
                e.id::text, 
                e.status, 
                e.module as domain, 
                e.created_at as started_at, 
                e.completed_at, 
                e.result_payload, 
                e.error_message, 
                w.name as workflow_name
            FROM execution_logs e
            LEFT JOIN workflows w ON e.module = w.domain AND w.status = 'active'
            WHERE e.user_email = %s
        """
        params = [x_user_email]
        
        if status:
            query += " AND e.status = %s"
            params.append(status)
            
        query += " ORDER BY e.created_at DESC LIMIT %s"
        params.append(limit)
        
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            
        # Due to LEFT JOIN and multiple workflows for a domain historically, group by execution ID to prevent duplicates
        seen = set()
        results = []
        for r in rows:
            if r[0] in seen:
                continue
            seen.add(r[0])
            results.append({
                "id": r[0],
                "status": r[1],
                "domain": r[2],
                "started_at": r[3].isoformat() if r[3] else None,
                "completed_at": r[4].isoformat() if r[4] else None,
                "result_payload": r[5],
                "error_message": r[6],
                "workflow_name": r[7]
            })
            
        return {"count": len(results), "results": results}
    finally:
        conn.close()
