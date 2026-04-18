from fastapi import APIRouter, HTTPException
from typing import List, Optional
from database import get_db_connection
from pydantic import BaseModel
import json

router = APIRouter()

class HRResult(BaseModel):
    id: str
    status: str
    created_at: str
    candidate_summary: Optional[str] = None
    scores: Optional[List[int]] = []

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
                (user_email,)
            )
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                log_id, status, created_at, result_payload, output_summary = row
                
                # Extract summary info for dashboard
                summary_text = "N/A"
                scores = []
                
                # Try to parse scores from result_payload or output_summary
                data = result_payload if result_payload else output_summary
                if data and isinstance(data, dict):
                    candidates = data.get("ranked_candidates", []) or data.get("results", [])
                    if isinstance(candidates, list) and candidates:
                        summary_text = f"{len(candidates)} candidates processed"
                        scores = [c.get("score", 0) for c in candidates if isinstance(c, dict)]
                
                results.append({
                    "id": str(log_id),
                    "status": status,
                    "created_at": created_at.isoformat(),
                    "candidate_summary": summary_text,
                    "scores": scores
                })
            
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@router.get("/hr/ping")
async def hr_ping():
    return {"ok": True, "module": "hr"}
