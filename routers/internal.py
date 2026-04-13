import os

from fastapi import APIRouter, HTTPException

from database import get_db_connection
from orchestration import (
    build_n8n_api_headers,
    create_execution_log,
    get_n8n_executions_for_request,
    get_execution_log,
    json_dumps,
    log_exception,
    merge_execution_log_output_summary,
    ping_n8n_health,
    post_with_retry,
    upsert_execution_log,
    update_execution_log,
)


router = APIRouter()


def _ensure_fields(payload: dict, required_fields: list[str]) -> None:
    for field_name in required_fields:
        if field_name not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {field_name}")


def _callback_base_url() -> str:
    return os.getenv("FASTAPI_CALLBACK_URL", os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")


def _error_summary(error: Exception | str, payload: dict, workflow: str) -> dict:
    return {
        "workflow": workflow,
        "error": str(error),
        "payload": payload,
    }


def _upsert_request_log(conn, payload: dict, module: str, default_status: str) -> str:
    request_id = payload.get("request_id")
    if request_id:
        return upsert_execution_log(
            conn,
            request_id,
            user_email=payload.get("user_email", "system"),
            module=module,
            input_payload=payload,
            status=default_status,
        )
    return create_execution_log(
        conn,
        user_email=payload.get("user_email", "system"),
        module=module,
        input_payload=payload,
        status=default_status,
    )


@router.post("/internal/invoice-result")
async def invoice_result(payload: dict):
    _ensure_fields(payload, ["invoice_id", "user_email"])

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO invoices (id, user_email, vendor_name, invoice_number, amount, invoice_date, line_items, raw_extracted, status, updated_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                ON CONFLICT (id) DO UPDATE SET
                  vendor_name = EXCLUDED.vendor_name,
                  invoice_number = EXCLUDED.invoice_number,
                  amount = EXCLUDED.amount,
                  invoice_date = EXCLUDED.invoice_date,
                  line_items = EXCLUDED.line_items,
                  raw_extracted = EXCLUDED.raw_extracted,
                  status = EXCLUDED.status,
                  updated_at = now()
                RETURNING id
                """,
                (
                    payload.get("invoice_id"),
                    payload.get("user_email"),
                    payload.get("vendor_name"),
                    payload.get("invoice_number"),
                    payload.get("amount"),
                    payload.get("invoice_date"),
                    json_dumps(payload.get("line_items")),
                    json_dumps(payload.get("raw_extracted")),
                    payload.get("status", "processing"),
                ),
            )
        conn.commit()

        request_id = _upsert_request_log(conn, payload, "invoice", payload.get("status", "completed"))

        if payload.get("amount") is not None:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO approvals (user_email, module, reference_id, title, description, payload, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    RETURNING id
                    """,
                    (
                        payload.get("user_email"),
                        "invoices",
                        payload.get("invoice_id"),
                        f"Approve invoice {payload.get('invoice_number')} for {payload.get('vendor_name')}",
                        "Auto-generated approval",
                        json_dumps(payload),
                        "pending",
                    ),
                )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        log_exception("Invoice callback failed", payload=payload)
        raise HTTPException(status_code=500, detail=f"Invoice callback failed: {exc}") from exc
    finally:
        conn.close()

    return {"status": "ok", "request_id": request_id}


@router.post("/internal/hr-result")
async def hr_result(payload: dict):
    _ensure_fields(payload, ["user_email", "candidate_name", "candidate_email"])

    conn = get_db_connection()
    try:
        request_id = payload.get("request_id")
        if request_id and get_execution_log(conn, request_id):
            merge_execution_log_output_summary(
                conn,
                request_id,
                {
                    "steps": {
                        "hr_result": payload,
                    }
                },
                status="completed",
                input_payload=payload,
            )
        else:
            request_id = _upsert_request_log(conn, payload, "hr", payload.get("status", "completed"))

        if payload.get("shortlisted"):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO approvals (user_email, module, title, description, payload, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    RETURNING id
                    """,
                    (
                        payload.get("user_email"),
                        "hr",
                        f"Candidate: {payload.get('candidate_name')}",
                        f"Candidate shortlisted: {payload.get('candidate_name')}",
                        json_dumps(payload),
                        "pending",
                    ),
                )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        log_exception("HR callback failed", payload=payload)
        raise HTTPException(status_code=500, detail=f"HR callback failed: {exc}") from exc
    finally:
        conn.close()

    return {"status": "ok", "request_id": request_id}


@router.post("/internal/triage-result")
async def triage_result(payload: dict):
    _ensure_fields(payload, ["user_email", "category", "email_subject", "email_from", "action_taken"])

    conn = get_db_connection()
    try:
        request_id = _upsert_request_log(conn, payload, "triage", payload.get("status", "completed"))
    except HTTPException:
        raise
    except Exception as exc:
        log_exception("Triage result callback failed", payload=payload)
        raise HTTPException(status_code=500, detail=f"Triage result callback failed: {exc}") from exc
    finally:
        conn.close()

    return {"status": "ok", "request_id": request_id}


@router.post("/internal/triage")
async def internal_triage(payload: dict):
    _ensure_fields(payload, ["user_email", "category", "email_data"])

    email_data = payload.get("email_data") or {}
    _ensure_fields(email_data, ["subject", "body", "from"])

    user_email = payload.get("user_email")
    category = (payload.get("category") or "").strip()
    cat = category.lower()
    conn = get_db_connection()
    request_id = None

    try:
        request_id = create_execution_log(
            conn,
            user_email=user_email,
            module="triage",
            input_payload=payload,
            status="created",
        )

        if cat == "recruitment":
            workflow = "hr_recruitment"
            n8n_url = os.getenv("N8N_HR_WEBHOOK_URL")
            if not n8n_url:
                error_message = "N8N_HR_WEBHOOK_URL not configured"
                update_execution_log(
                    conn,
                    request_id,
                    status="failed_to_trigger",
                    output_summary=_error_summary(error_message, payload, workflow),
                )
                return {
                    "request_id": request_id,
                    "status": "failed_to_trigger",
                    "workflow": workflow,
                    "error": error_message,
                }

            body = {
                "request_id": request_id,
                "workflow_type": workflow,
                "payload": {
                    "email_data": email_data,
                    "user_email": user_email,
                },
                "callback_url": f"{_callback_base_url()}/api/execution-callback",
            }

            update_execution_log(conn, request_id, status="triggering", output_summary={"workflow": workflow})

            try:
                response = await post_with_retry(
                    n8n_url,
                    json_body=body,
                    headers=build_n8n_api_headers(),
                    timeout=15.0,
                    attempts=3,
                )
            except Exception as exc:
                log_exception(
                    "Failed to trigger HR workflow",
                    request_id=request_id,
                    n8n_url=n8n_url,
                    payload=body,
                )
                update_execution_log(
                    conn,
                    request_id,
                    status="failed_to_trigger",
                    output_summary=_error_summary(exc, body, workflow),
                )
                return {
                    "request_id": request_id,
                    "status": "failed_to_trigger",
                    "workflow": workflow,
                    "error": str(exc),
                }

            update_execution_log(
                conn,
                request_id,
                status="running",
                output_summary={
                    "workflow": workflow,
                    "n8n_status_code": response.status_code,
                    "n8n_response_text": response.text[:500],
                },
            )
            return {"request_id": request_id, "status": "triggered", "workflow": workflow}

        if cat == "invoice":
            update_execution_log(
                conn,
                request_id,
                status="stubbed",
                output_summary={"message": "Invoice workflow is stubbed"},
            )
            return {"request_id": request_id, "status": "stubbed", "message": "Invoice workflow is stubbed"}

        update_execution_log(
            conn,
            request_id,
            status="completed",
            output_summary={"message": "Category ignored"},
        )
        return {"request_id": request_id, "status": "ignored", "message": "Category ignored"}
    except HTTPException:
        raise
    except Exception as exc:
        log_exception("Unhandled error in internal triage", payload=payload, request_id=request_id)
        if request_id:
            try:
                update_execution_log(
                    conn,
                    request_id,
                    status="failed",
                    output_summary=_error_summary(exc, payload, "triage"),
                )
            except Exception:
                log_exception("Failed to persist triage error", request_id=request_id)
        raise HTTPException(status_code=500, detail=f"Internal triage failed for request_id {request_id}") from exc
    finally:
        conn.close()


@router.get("/internal/n8n/executions/{request_id}")
async def get_n8n_execution(request_id: str):
    try:
        return await get_n8n_executions_for_request(request_id)
    except Exception as exc:
        log_exception("Failed to fetch n8n executions", request_id=request_id)
        raise HTTPException(status_code=502, detail=f"Failed to query n8n executions: {exc}") from exc


@router.get("/n8n/ping")
async def n8n_ping():
    try:
        health = await ping_n8n_health()
        return {"status": "ok", **health}
    except Exception as exc:
        log_exception("Failed to ping n8n health endpoint")
        raise HTTPException(status_code=502, detail=f"Failed to ping n8n: {exc}") from exc
