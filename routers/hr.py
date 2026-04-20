import json
import os
import uuid
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_db_connection
from orchestration import build_n8n_webhook_headers

router = APIRouter()


class HRResult(BaseModel):
    id: str
    status: str
    created_at: str
    candidate_summary: Optional[str] = None
    scores: Optional[List[int]] = []


class HRWebhookConnect(BaseModel):
    user_email: str
    hr_webhook_url: str
    input_format: str = "json"
    callback_url: Optional[str] = None
    secret: Optional[str] = None


class ScreeningCriteria(BaseModel):
    role: str
    required_language: str
    experience_level: str  # fresher | mid | senior | any
    min_years_experience: int = 0


def _backend_public() -> str:
    return (os.getenv("BACKEND_PUBLIC_URL") or os.getenv("FASTAPI_BASE_URL") or "http://localhost:8000").rstrip(
        "/"
    )


def _ensure_user(conn, email: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (email) VALUES (%s) ON CONFLICT (email) DO NOTHING",
            (email,),
        )
    conn.commit()


@router.get("/hr/ping")
async def hr_ping():
    return {"ok": True, "module": "hr"}


@router.post("/hr/criteria/{user_email}")
async def set_hr_criteria(user_email: str, criteria: ScreeningCriteria):
    """Upsert screening criteria for a user into hr_connections."""
    conn = get_db_connection()
    try:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO hr_connections (user_email, screening_criteria, is_active, webhook_configured, last_sync)
                    VALUES (%s, %s, true, COALESCE((SELECT webhook_configured FROM hr_connections WHERE user_email = %s), true), now())
                    ON CONFLICT (user_email) DO UPDATE SET
                        screening_criteria = EXCLUDED.screening_criteria,
                        last_sync = now()
                    """,
                    (user_email, json.dumps(criteria.model_dump()), user_email),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            # Column may not exist yet — store criteria as best-effort
        return {"saved": True, "criteria": criteria.model_dump()}
    finally:
        conn.close()


@router.get("/hr/criteria/{user_email}")
async def get_hr_criteria(user_email: str):
    """Fetch screening criteria for a user, returning defaults if not present."""
    default = {
        "role": "General Position",
        "required_language": "English",
        "experience_level": "any",
        "min_years_experience": 0,
    }
    conn = get_db_connection()
    try:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT screening_criteria FROM hr_connections WHERE user_email = %s LIMIT 1", (user_email,))
                row = cur.fetchone()
            if row and row[0]:
                return {"criteria": row[0]}
        except Exception:
            conn.rollback()  # Column may not exist
        return {"criteria": default}
    finally:
        conn.close()


@router.get("/hr/status/{user_email}")
async def hr_status(user_email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT webhook_url, is_active, COALESCE(webhook_configured, false)
                FROM hr_connections
                WHERE user_email = %s
                LIMIT 1
                """,
                (user_email,),
            )
            hc = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*) FILTER (WHERE status = 'completed'),
                       MAX(created_at)
                FROM execution_logs
                WHERE user_email = %s AND module = 'hr'
                """,
                (user_email,),
            )
            total_row = cur.fetchone()
            total_processed = int(total_row[0] or 0)
            last_run = total_row[1]

        if not hc:
            return {
                "connected": False,
                "webhook_configured": False,
                "last_run": last_run.isoformat() if last_run else None,
                "total_processed": total_processed,
            }

        connected = bool(hc[1])
        webhook_configured = bool(hc[2] or hc[0])

        return {
            "connected": connected,
            "webhook_configured": webhook_configured,
            "last_run": last_run.isoformat() if last_run else None,
            "total_processed": total_processed,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") from e
    finally:
        conn.close()


@router.post("/webhooks/hr")
async def hr_webhook_connect(body: HRWebhookConnect):
    execution_id = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        _ensure_user(conn, body.user_email)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hr_connections (
                    user_email, webhook_url, input_format, secret, is_active, webhook_configured, last_sync
                )
                VALUES (%s, %s, %s, %s, true, true, now())
                ON CONFLICT (user_email) DO UPDATE SET
                    webhook_url = EXCLUDED.webhook_url,
                    input_format = EXCLUDED.input_format,
                    secret = EXCLUDED.secret,
                    is_active = true,
                    webhook_configured = true,
                    last_sync = now()
                """,
                (body.user_email, body.hr_webhook_url, body.input_format, body.secret),
            )

            cur.execute(
                """
                SELECT n8n_webhook_url FROM workflows
                WHERE domain = 'hr' AND status = 'active' LIMIT 1
                """
            )
            wf = cur.fetchone()
            if not wf or not wf[0]:
                conn.rollback()
                raise HTTPException(status_code=500, detail="HR workflow not configured in database")

            n8n_webhook_url = wf[0]

            cur.execute(
                """
                INSERT INTO execution_logs (id, user_email, module, status, input_payload, created_at, updated_at)
                VALUES (%s, %s, 'hr', 'pending', %s, now(), now())
                """,
                (
                    execution_id,
                    body.user_email,
                    json.dumps(
                        {
                            "hr_webhook_url": body.hr_webhook_url,
                            "input_format": body.input_format,
                        }
                    ),
                ),
            )
        conn.commit()
        # fetch screening_criteria (if any) to include in the webhook payload
        screening_criteria = {}
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT screening_criteria FROM hr_connections WHERE user_email = %s LIMIT 1", (body.user_email,))
                sc_row = cur.fetchone()
            screening_criteria = sc_row[0] if sc_row and sc_row[0] else {}
        except Exception:
            conn.rollback()  # reset transaction after column-missing error

        backend = _backend_public()
        callback = f"{backend}/api/execution-callback"
        webhook_payload = {
            "request_id": execution_id,
            "callback_url": callback,
            "n8n_callback_secret": os.getenv("N8N_CALLBACK_SECRET", ""),
            "payload": {
                "user_email": body.user_email,
                "hr_webhook_url": body.hr_webhook_url,
                "input_format": body.input_format,
                "screening_criteria": screening_criteria,
            },
        }

        headers = build_n8n_webhook_headers()
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(n8n_webhook_url, json=webhook_payload, headers=headers)
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE execution_logs
                    SET status = 'failed', error_message = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (str(e), execution_id),
                )
            conn.commit()
            raise HTTPException(status_code=502, detail=f"n8n webhook failed: {e}") from e

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE execution_logs SET status = 'running', updated_at = now() WHERE id = %s",
                (execution_id,),
            )
        conn.commit()

        return {"execution_id": execution_id, "status": "processing"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HR connect failed: {e}") from e
    finally:
        conn.close()


@router.post("/hr/test/{user_email}")
async def hr_test(user_email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM hr_connections WHERE user_email = %s AND is_active = true",
                (user_email,),
            )
            if not cur.fetchone():
                return {"ok": False, "message": "No HR webhook configured"}

            cur.execute(
                """
                SELECT n8n_webhook_url FROM workflows
                WHERE domain = 'hr' AND status = 'active' LIMIT 1
                """
            )
            wf = cur.fetchone()
        if not wf or not wf[0]:
            raise HTTPException(status_code=500, detail="HR workflow not configured in database")

        n8n_url = wf[0]
        dummy = {
            "request_id": f"test-{uuid.uuid4()}",
            "test": True,
            "user_email": user_email,
            "payload": {"message": "connection test"},
        }
        headers = build_n8n_webhook_headers()
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(n8n_url, json=dummy, headers=headers)
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "message": f"n8n returned {resp.status_code}: {resp.text[:200]}",
                }
        return {"ok": True, "message": "Connection successful"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Test request failed: {e}") from e
    finally:
        conn.close()


@router.delete("/hr/disconnect/{user_email}")
async def hr_disconnect(user_email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hr_connections WHERE user_email = %s", (user_email,))
        conn.commit()
    finally:
        conn.close()
    return {"disconnected": True}


@router.get("/hr/{user_email}")
async def get_hr_results(user_email: str):
    """
    Fetches the latest HR ranking/shortlist results for a specific user.
    Used by the frontend dashboard to display candidate status.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, status, created_at, result_payload, output_summary
                FROM execution_logs
                WHERE user_email = %s AND module = 'hr'
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (user_email,),
            )
            rows = cur.fetchall()

            results = []
            for row in rows:
                log_id, status, created_at, result_payload, output_summary = row

                summary_text = "N/A"
                scores = []

                data = result_payload if result_payload else output_summary
                if data and isinstance(data, dict):
                    candidates = data.get("ranked_candidates", []) or data.get("results", [])
                    if isinstance(candidates, list) and candidates:
                        summary_text = f"{len(candidates)} candidates processed"
                        scores = [c.get("score", 0) for c in candidates if isinstance(c, dict)]

                results.append(
                    {
                        "id": str(log_id),
                        "status": status,
                        "created_at": created_at.isoformat(),
                        "candidate_summary": summary_text,
                        "scores": scores,
                    }
                )

            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()
