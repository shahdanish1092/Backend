import json
from typing import Any

from fastapi import APIRouter, HTTPException, Header

from database import get_db_connection

router = APIRouter()


def _jsonish(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return val


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, x_user_email: str | None = Header(None, alias="X-User-Email")):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, status, module, created_at, updated_at, result_payload, error_message, user_email
                FROM execution_logs
                WHERE id = %s
                """,
                (execution_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Execution not found")

    exec_id, status, module, created_at, updated_at, result_payload, error_message, owner_email = row
    if x_user_email:
        if (owner_email or "").strip().lower() != x_user_email.strip().lower():
            raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "id": exec_id,
        "status": status,
        "module": module,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "result_payload": _jsonish(result_payload),
        "error_message": error_message,
    }
