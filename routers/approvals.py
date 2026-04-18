from fastapi import APIRouter, HTTPException
from typing import List, Optional
from database import get_db_connection
from pydantic import BaseModel
import json

router = APIRouter()

class ApprovalResult(BaseModel):
    id: str
    status: str
    created_at: str
    summary: Optional[str] = None
    approver: Optional[str] = None

@router.get("/approvals/{user_email}")
async def get_approval_results(user_email: str):
    """
    Fetches the latest Approval requests/results for a specific user.
    Used by the frontend dashboard to display pending actions.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, status, created_at, result_payload, output_summary
                FROM execution_logs
                WHERE user_email = %s AND module = 'approval'
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (user_email,)
            )
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                log_id, status, created_at, result_payload, output_summary = row
                
                # Extract summary info for dashboard
                summary_text = "N/A"
                approver = "N/A"
                
                # Check output_summary or result_payload
                data = result_payload if result_payload else output_summary
                if data and isinstance(data, dict):
                    wf = data.get("workflow", "")
                    summary_text = f"Approval for {wf}" if wf else "Approval request"
                    approver = data.get("approver_email", "TBD")
                
                results.append({
                    "id": str(log_id),
                    "status": status,
                    "created_at": created_at.isoformat(),
                    "summary": summary_text,
                    "approver": approver
                })
            
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@router.get("/approvals/ping")
async def approvals_ping():
    return {"ok": True, "module": "approvals"}
