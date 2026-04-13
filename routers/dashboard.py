from fastapi import APIRouter, HTTPException

from database import get_db_connection

router = APIRouter()


@router.get("/status")
async def status():
    return {"status": "ok", "service": "dashboard"}


@router.get("/status/{user_email}")
async def user_status(user_email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, module, status, created_at, updated_at, output_summary
                FROM execution_logs
                WHERE user_email = %s
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 10
                """,
                (user_email,),
            )
            rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch status: {exc}") from exc
    finally:
        conn.close()

    return {
        "user_email": user_email,
        "executions": [
            {
                "request_id": row[0],
                "module": row[1],
                "status": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "updated_at": row[4].isoformat() if row[4] else None,
                "output_summary": row[5] or {},
            }
            for row in rows
        ],
    }
