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
    # Try to use groq if available, otherwise fallback to simple heuristic
    try:
        import groq

        if hasattr(groq, "Client"):
            client = groq.Client()
            prompt = (
                "You are an intent classifier for Spatial+ office automation. "
                "Given user text, return ONLY valid JSON with fields: domain, action, parameters. "
                "Domains: hr, invoices, meetings, approvals, general."
            )
            try:
                resp = client.chat.completions.create(
                    model=os.getenv("GROQ_MODEL", "llama3-70b-8192"),
                    messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
                )
                content = None
                if hasattr(resp, "choices") and resp.choices:
                    choice = resp.choices[0]
                    message = getattr(choice, "message", None)
                    if message:
                        content = getattr(message, "content", None) or str(message)
                if content:
                    try:
                        return json.loads(content)
                    except Exception:
                        # try to extract JSON object
                        import re

                        m = re.search(r"\{.*\}", content, re.DOTALL)
                        if m:
                            return json.loads(m.group())
            except Exception:
                pass
    except Exception:
        pass

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

    conn = get_db_connection()
    request_id = None
    try:
        # find a workflow for this domain
        with conn.cursor() as cur:
            cur.execute(
                "SELECT n8n_id, name FROM workflows WHERE domain = %s AND status = 'active' ORDER BY updated_at DESC LIMIT 1",
                (domain,),
            )
            wf = cur.fetchone()

        if not wf:
            # create execution log as failed_to_trigger
            request_id = create_execution_log(conn, user_email=user_email, module=domain, input_payload={"text": text, "connectors": active_connectors}, status="failed_to_trigger")
            return {"execution_id": request_id, "domain": domain, "action": classification.get("action"), "message": f"No workflow found for domain {domain}"}

        n8n_id, workflow_name = wf[0], wf[1]

        # create execution log
        request_id = create_execution_log(conn, user_email=user_email, module=domain, input_payload={"text": text, "connectors": active_connectors}, status="pending")

        # trigger n8n
        parameters = {"text": text, "connectors": active_connectors, "user_email": user_email}
        try:
            resp = await trigger_n8n_workflow(n8n_id, parameters, request_id)
        except Exception as exc:
            merge_execution_log_output_summary(conn, request_id, {"error": str(exc)}, status="failed_to_trigger")
            return {"execution_id": request_id, "domain": domain, "action": classification.get("action"), "message": "Failed to trigger workflow", "error": str(exc)}

        # If webhook triggered, mark as 'triggered'; otherwise keep 'running' for API-triggered runs
        new_status = "triggered" if isinstance(resp, dict) and resp.get("method") == "webhook" else "running"
        merge_execution_log_output_summary(conn, request_id, {"workflow": workflow_name, "n8n_response": resp}, status=new_status)

        return {"execution_id": request_id, "domain": domain, "action": classification.get("action"), "message": f"Workflow started. Tracking execution {request_id}.", "trigger_method": resp.get("method") if isinstance(resp, dict) else None}
    finally:
        conn.close()


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, x_user_email: str | None = Header(None)):
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Missing X-User-Email header")

    conn = get_db_connection()
    try:
        row = get_execution_log(conn, execution_id)
        if not row:
            raise HTTPException(status_code=404, detail="Execution not found")
        if row.get("user_email") != x_user_email:
            raise HTTPException(status_code=403, detail="Forbidden")
        return row
    finally:
        conn.close()


@router.get("/executions")
async def list_executions(user_email: str, status: str | None = None, limit: int = 20):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if status:
                cur.execute(
                    "SELECT id::text, user_email, module, status, input_payload, output_summary, created_at, updated_at FROM execution_logs WHERE user_email = %s AND status = %s ORDER BY created_at DESC LIMIT %s",
                    (user_email, status, limit),
                )
            else:
                cur.execute(
                    "SELECT id::text, user_email, module, status, input_payload, output_summary, created_at, updated_at FROM execution_logs WHERE user_email = %s ORDER BY created_at DESC LIMIT %s",
                    (user_email, limit),
                )
            rows = cur.fetchall()
        results = [
            {
                "id": r[0],
                "user_email": r[1],
                "module": r[2],
                "status": r[3],
                "input_payload": r[4],
                "output_summary": r[5],
                "created_at": r[6],
                "updated_at": r[7],
            }
            for r in rows
        ]
        return {"count": len(results), "results": results}
    finally:
        conn.close()
