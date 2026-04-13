import asyncio
import json
import logging
import os
from typing import Any

import httpx


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
            SELECT id::text, user_email, module, status, input_payload, output_summary, created_at, updated_at
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
    api_key = os.getenv("N8N_API_KEY")
    if not api_key:
        return {}

    custom_header = os.getenv("N8N_API_AUTH_HEADER")
    if custom_header:
        return {custom_header: api_key}

    auth_mode = os.getenv("N8N_API_AUTH_MODE", "x-api-key").strip().lower()
    if auth_mode in {"bearer", "authorization"}:
        return {"Authorization": f"Bearer {api_key}"}
    return {"X-N8N-API-KEY": api_key}


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
    headers_to_try: list[tuple[str, dict[str, str]]] = []
    if api_key:
        headers_to_try.append(("x-api-key", {"X-N8N-API-KEY": api_key}))
        headers_to_try.append(("bearer", {"Authorization": f"Bearer {api_key}"}))
    else:
        headers_to_try.append(("none", {}))

    log_info("Fetching n8n executions", url=url, request_id=request_id, auth_modes=[name for name, _ in headers_to_try])

    async with httpx.AsyncClient(timeout=20.0) as client:
        last_response: httpx.Response | None = None
        auth_mode_used = "none"
        for index, (auth_mode, headers) in enumerate(headers_to_try):
            response = await client.get(url, headers=headers)
            last_response = response
            auth_mode_used = auth_mode
            if response.status_code == 401 and index < len(headers_to_try) - 1:
                log_warning("n8n execution lookup unauthorized; retrying with fallback auth", url=url, auth_mode=auth_mode)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        else:
            assert last_response is not None
            last_response.raise_for_status()

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
