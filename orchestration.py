import asyncio
import json
import logging
import os
from datetime import timezone
from typing import Any

import httpx
import base64


logger = logging.getLogger("office_automation.orchestration")

_UNSET = object()


def _json_default(value: Any) -> str:
    return str(value)


def json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=_json_default)


def log_info(message: str, **context: Any) -> None:
    logger.info("%s | context=%s", message, context)


def log_warning(message: str, **context: Any) -> None:
    logger.warning("%s | context=%s", message, context)


def log_exception(message: str, **context: Any) -> None:
    logger.exception("%s | context=%s", message, context)


def create_execution_log(conn, user_email: str, module: str, input_payload: Any, status: str, output_summary: Any = None) -> str:
    log_info(
        "Creating execution log",
        user_email=user_email,
        module=module,
        status=status,
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO execution_logs (user_email, module, input_payload, output_summary, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_email,
                module,
                json_dumps(input_payload),
                json_dumps(output_summary),
                status,
            ),
        )
        row = cur.fetchone()
    conn.commit()
    request_id = str(row[0])
    log_info("Execution log created", request_id=request_id, module=module)
    return request_id


def upsert_execution_log(
    conn,
    request_id: str,
    *,
    user_email: str,
    module: str,
    input_payload: Any,
    status: str,
    output_summary: Any = None,
) -> str:
    log_info("Upserting execution log", request_id=request_id, module=module, status=status)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO execution_logs (id, user_email, module, input_payload, output_summary, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
              user_email = EXCLUDED.user_email,
              module = EXCLUDED.module,
              input_payload = EXCLUDED.input_payload,
              output_summary = EXCLUDED.output_summary,
              status = EXCLUDED.status,
              updated_at = now()
            RETURNING id
            """,
            (
                request_id,
                user_email,
                module,
                json_dumps(input_payload),
                json_dumps(output_summary),
                status,
            ),
        )
        row = cur.fetchone()
    conn.commit()
    return str(row[0])


def update_execution_log(
    conn,
    request_id: str,
    *,
    status: str | None = None,
    output_summary: Any = _UNSET,
    input_payload: Any = _UNSET,
) -> int:
    if not request_id:
        return

    fields = ["updated_at = now()"]
    params: list[Any] = []

    if status is not None:
        fields.append("status = %s")
        params.append(status)
        # If the execution reached a terminal state, set completed_at timestamp
        if status in {"completed", "failed", "timeout"}:
            fields.append("completed_at = now()")
    if output_summary is not _UNSET:
        fields.append("output_summary = %s")
        params.append(json_dumps(output_summary))
    if input_payload is not _UNSET:
        fields.append("input_payload = %s")
        params.append(json_dumps(input_payload))

    params.append(request_id)
    sql = f"UPDATE execution_logs SET {', '.join(fields)} WHERE id = %s"

    log_info(
        "Updating execution log",
        request_id=request_id,
        status=status,
        output_summary_included=output_summary is not _UNSET,
        input_payload_included=input_payload is not _UNSET,
    )
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rowcount = cur.rowcount
    conn.commit()
    return rowcount


def get_execution_log(conn, request_id: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id::text, user_email, module, status, input_payload, output_summary, created_at, updated_at, completed_at
            FROM execution_logs
            WHERE id = %s
            """,
            (request_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "user_email": row[1],
        "module": row[2],
        "status": row[3],
        "input_payload": row[4],
        "output_summary": row[5],
        "created_at": row[6],
        "updated_at": row[7],
        "completed_at": row[8],
    }


def _merge_output_summary(existing: Any, patch: Any) -> Any:
    if existing is None:
        return patch
    if patch is None:
        return existing
    if isinstance(existing, dict) and isinstance(patch, dict):
        merged = dict(existing)
        for key, value in patch.items():
            if key in merged:
                merged[key] = _merge_output_summary(merged[key], value)
            else:
                merged[key] = value
        return merged
    return patch


def merge_execution_log_output_summary(conn, request_id: str, patch: Any, *, status: str | None = None, input_payload: Any = _UNSET) -> int:
    existing = get_execution_log(conn, request_id)
    current_summary = existing.get("output_summary") if existing else None
    next_summary = _merge_output_summary(current_summary, patch)
    return update_execution_log(
        conn,
        request_id,
        status=status,
        output_summary=next_summary,
        input_payload=input_payload,
    )


def build_n8n_api_headers() -> dict[str, str]:
    """Build headers for n8n API calls.

    Always use the `X-N8N-API-KEY` header with the value from `N8N_API_KEY`.
    This keeps auth consistent across environments and avoids bearer/basic variations.
    """
    api_key = os.getenv("N8N_API_KEY")
    headers: dict[str, str] = {}
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    return headers


def build_n8n_webhook_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}

    backend_secret = os.getenv("BACKEND_WEBHOOK_SECRET") or os.getenv("N8N_CALLBACK_SECRET")
    if backend_secret:
        headers["X-Backend-Secret"] = backend_secret

    auth_user = os.getenv("N8N_BASIC_AUTH_USER")
    auth_pass = os.getenv("N8N_BASIC_AUTH_PASSWORD")
    if auth_user and auth_pass:
        basic_auth_b64 = base64.b64encode(f"{auth_user}:{auth_pass}".encode()).decode()
        headers["Authorization"] = f"Basic {basic_auth_b64}"

    return headers


def resolve_workflow_webhook_url(
    conn,
    domain: str,
    *,
    preferred_name_substring: str | None = None,
    default_path: str | None = None,
) -> str | None:
    order_case = ""
    params: list[Any] = [domain]
    if preferred_name_substring:
        order_case = "CASE WHEN lower(name) LIKE %s THEN 0 ELSE 1 END,"
        params.append(f"%{preferred_name_substring.lower()}%")

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT n8n_webhook_url
            FROM workflows
            WHERE domain = %s
              AND status = 'active'
              AND coalesce(n8n_webhook_url, '') <> ''
            ORDER BY {order_case} updated_at DESC NULLS LAST
            LIMIT 1
            """,
            tuple(params),
        )
        row = cur.fetchone()
    if row and row[0]:
        return row[0]

    webhook_base = os.getenv("N8N_WEBHOOK_BASE_URL") or os.getenv("N8N_BASE_URL")
    if webhook_base and default_path:
        return f"{webhook_base.rstrip('/')}/webhook/{default_path.lstrip('/')}"
    return None


def get_valid_google_token(user_email: str) -> tuple[str, Any]:
    from auth.google_oauth import refresh_token_if_needed
    from database import get_db_connection

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT access_token, refresh_token, token_expiry FROM google_tokens WHERE user_email = %s",
                (user_email,),
            )
            token_row = cur.fetchone()

        if not token_row:
            raise RuntimeError("User has not connected Google account")

        access_token, refresh_token, token_expiry = token_row
        if token_expiry and token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)

        creds = refresh_token_if_needed(access_token, refresh_token, token_expiry)
        next_access_token = creds.token or access_token
        next_refresh_token = creds.refresh_token or refresh_token
        next_expiry = creds.expiry or token_expiry
        if next_expiry and next_expiry.tzinfo is None:
            next_expiry = next_expiry.replace(tzinfo=timezone.utc)

        if (
            next_access_token != access_token
            or next_refresh_token != refresh_token
            or next_expiry != token_expiry
        ):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE google_tokens
                    SET access_token = %s,
                        refresh_token = %s,
                        token_expiry = %s,
                        updated_at = now()
                    WHERE user_email = %s
                    """,
                    (next_access_token, next_refresh_token, next_expiry, user_email),
                )
            conn.commit()

        return next_access_token, next_expiry
    finally:
        conn.close()


async def post_with_retry(
    url: str,
    *,
    json_body: Any,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    attempts: int = 3,
) -> httpx.Response:
    headers = headers or {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                log_info("Calling external HTTP endpoint", url=url, attempt=attempt)
                response = await client.post(url, json=json_body, headers=headers)
                response.raise_for_status()
                log_info(
                    "External HTTP call succeeded",
                    url=url,
                    attempt=attempt,
                    status_code=response.status_code,
                )
                return response
            except Exception as exc:
                last_error = exc
                log_warning(
                    "External HTTP call failed",
                    url=url,
                    attempt=attempt,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                if attempt < attempts:
                    await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

    assert last_error is not None
    raise RuntimeError(f"HTTP POST failed after {attempts} attempts: {last_error}")


async def get_n8n_executions_for_request(request_id: str) -> dict[str, Any]:
    n8n_base_url = os.getenv("N8N_BASE_URL")
    if not n8n_base_url:
        raise RuntimeError("N8N_BASE_URL is not configured")

    url = f"{n8n_base_url.rstrip('/')}/rest/executions"
    api_key = os.getenv("N8N_API_KEY")
    auth_mode_used = "none"

    log_info("Fetching n8n executions", url=url, request_id=request_id, headers=list(("X-N8N-API-KEY",) if api_key else ()))

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Try X-N8N-API-KEY first for compatibility with API-key-configured instances
        headers = {"X-N8N-API-KEY": api_key} if api_key else {}
        response = await client.get(url, headers=headers)

        # If API key header yields 401, fall back to Bearer Authorization
        if response.status_code == 401 and api_key:
            log_warning("n8n returned 401 with X-N8N-API-KEY, retrying with Bearer Authorization", url=url)
            headers = {"Authorization": f"Bearer {api_key}"}
            response = await client.get(url, headers=headers)
            auth_mode_used = "bearer"
        elif api_key:
            auth_mode_used = "x-n8n-api-key"

        try:
            response.raise_for_status()
        except Exception:
            log_warning("Failed to fetch n8n executions", url=url, status_code=response.status_code, text=response.text)
            response.raise_for_status()

        try:
            payload = response.json()
        except Exception:
            payload = {}

    executions = payload.get("data", payload if isinstance(payload, list) else [])
    matches = [item for item in executions if request_id in json_dumps(item)]
    return {"request_id": request_id, "matches": matches, "count": len(matches), "auth_mode": auth_mode_used}


async def ping_n8n_health() -> dict[str, Any]:
    n8n_base_url = os.getenv("N8N_BASE_URL")
    if not n8n_base_url:
        raise RuntimeError("N8N_BASE_URL is not configured")

    url = f"{n8n_base_url.rstrip('/')}/healthz"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        try:
            body = response.json()
        except ValueError:
            body = response.text
    return {"base_url": n8n_base_url.rstrip("/"), "status_code": response.status_code, "body": body}


async def trigger_n8n_via_webhook(workflow_id: str, payload: dict[str, Any], execution_id: str) -> dict[str, Any]:
    """Trigger a workflow run by calling the workflow's Webhook trigger.

    Uses N8N_WEBHOOK_BASE_URL and N8N_WEBHOOK_PATH (or falls back to a sensible default).
    Webhook calls include the shared backend secret header validated inside n8n.
    Returns a dict describing the response.
    """
    webhook_base = os.getenv("N8N_WEBHOOK_BASE_URL") or os.getenv("N8N_BASE_URL")
    if not webhook_base:
        raise RuntimeError("N8N_WEBHOOK_BASE_URL or N8N_BASE_URL is not configured")

    webhook_path = os.getenv("N8N_WEBHOOK_PATH") or f"execute-workflow-{workflow_id}"

    backend_public = os.getenv("BACKEND_PUBLIC_URL") or os.getenv("FASTAPI_BASE_URL") or os.getenv("FASTAPI_CALLBACK_URL")
    callback_url = None
    if backend_public:
        callback_url = f"{backend_public.rstrip('/')}/api/webhooks/n8n/callback/{execution_id}"

    url = f"{webhook_base.rstrip('/')}/webhook/{webhook_path}"

    body: dict[str, Any] = {"request_id": execution_id}
    if callback_url:
        body["callback_url"] = callback_url
    # Provide backend base URL explicitly so n8n workflows don't need to access env vars
    if backend_public:
        body["backend_base_url"] = backend_public.rstrip("/")
    # Provide callback secret so n8n can send it back without needing $env access
    callback_secret = os.getenv("N8N_CALLBACK_SECRET")
    if callback_secret:
        body["n8n_callback_secret"] = callback_secret
    # include the original payload as 'input' and also surface common keys
    body["input"] = payload or {}
    if isinstance(payload, dict):
        for k in ("text", "user_email", "connectors"):
            if k in payload:
                body[k] = payload[k]

    headers = build_n8n_webhook_headers()
    resp = await post_with_retry(url, json_body=body, headers=headers, timeout=20.0, attempts=3)
    try:
        return {"method": "webhook", "status_code": resp.status_code, "json": resp.json()}
    except Exception:
        return {"method": "webhook", "status_code": resp.status_code, "text": resp.text}


async def trigger_n8n_via_api(workflow_id: str, payload: dict[str, Any], execution_id: str) -> dict[str, Any]:
    """Fallback: trigger a workflow via the n8n REST API using the API key.

    Posts to: {N8N_BASE_URL}/api/v1/workflows/{workflow_id}/run
    """
    n8n_base_url = os.getenv("N8N_BASE_URL")
    if not n8n_base_url:
        raise RuntimeError("N8N_BASE_URL is not configured")

    backend_public = os.getenv("BACKEND_PUBLIC_URL") or os.getenv("FASTAPI_BASE_URL") or os.getenv("FASTAPI_CALLBACK_URL")
    callback_url = None
    if backend_public:
        callback_url = f"{backend_public.rstrip('/')}/api/webhooks/n8n/callback/{execution_id}"

    url = f"{n8n_base_url.rstrip('/')}/api/v1/workflows/{workflow_id}/run"
    body: dict[str, Any] = {"execution_id": execution_id, "input": payload or {}}
    if callback_url:
        body["callback_url"] = callback_url
    # Provide backend base URL explicitly so n8n workflows don't need to access env vars
    if backend_public:
        body["backend_base_url"] = backend_public.rstrip("/")
    # Provide callback secret so n8n can send it back without needing $env access
    callback_secret = os.getenv("N8N_CALLBACK_SECRET")
    if callback_secret:
        body["n8n_callback_secret"] = callback_secret

    headers = build_n8n_api_headers()
    headers.setdefault("ngrok-skip-browser-warning", "true")

    resp = await post_with_retry(url, json_body=body, headers=headers, timeout=20.0, attempts=3)
    try:
        return {"method": "api", "status_code": resp.status_code, "json": resp.json()}
    except Exception:
        return {"method": "api", "status_code": resp.status_code, "text": resp.text}


async def trigger_n8n_workflow(workflow_id: str, payload: dict[str, Any], execution_id: str) -> dict[str, Any]:
    """Primary entry: attempt webhook trigger first, then fall back to REST API if webhook fails.

    Returns a dict with at least a `method` key indicating `webhook` or `api` and response details.
    Raises on unrecoverable errors.
    """
    # Try webhook first
    try:
        return await trigger_n8n_via_webhook(workflow_id, payload, execution_id)
    except Exception as exc:
        log_warning("Webhook trigger failed, falling back to REST API", workflow_id=workflow_id, error=str(exc))

    # Fallback to API trigger
    return await trigger_n8n_via_api(workflow_id, payload, execution_id)


def update_execution_status(conn, execution_id: str, status: str, result: dict | None = None, error: str | None = None) -> int:
    """Helper to persist an execution status update into execution_logs.

    Uses merge_execution_log_output_summary to merge the result payload and set status.
    Returns number of rows updated.
    """
    patch: dict[str, Any] = {}
    if result is not None:
        patch["result"] = result
    if error is not None:
        patch["error"] = str(error)

    try:
        return merge_execution_log_output_summary(conn, execution_id, patch, status=status)
    except Exception as exc:
        log_exception("Failed to update execution status", request_id=execution_id, error=exc)
        raise
