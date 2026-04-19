from fastapi import APIRouter, HTTPException

from database import get_db_connection

router = APIRouter()


@router.get("/status")
async def status():
    return {"status": "ok", "service": "dashboard"}


import httpx
from datetime import datetime, timezone
import os

@router.get("/status/{user_email}")
async def user_status(user_email: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # invocies
            cur.execute("SELECT COUNT(*) FROM execution_logs WHERE user_email = %s AND module IN ('invoice', 'invoices') AND status = 'completed'", (user_email,))
            invoices_processed = cur.fetchone()[0]
            
            # meetings
            cur.execute("SELECT COUNT(*) FROM execution_logs WHERE user_email = %s AND module IN ('meeting', 'meetings') AND status = 'completed'", (user_email,))
            meetings_summarized = cur.fetchone()[0]
            
            # approvals
            cur.execute("SELECT COUNT(*) FROM execution_logs WHERE user_email = %s AND module IN ('approval', 'approvals') AND status = 'pending'", (user_email,))
            pending_approvals = cur.fetchone()[0]
            
            # recent activity
            cur.execute(
                """
                SELECT id::text, module, status, created_at, result_payload
                FROM execution_logs
                WHERE user_email = %s
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (user_email,)
            )
            rows = cur.fetchall()
            
            recent_activity = []
            now = datetime.now(timezone.utc)
            for r in rows:
                exec_id, module, status, created_at, result_payload = r
                
                # relative time
                rel_time = "just now"
                if created_at:
                    diff = now - created_at
                    if diff.days > 0:
                        rel_time = f"{diff.days}d ago"
                    elif diff.seconds > 3600:
                        rel_time = f"{diff.seconds // 3600}h ago"
                    elif diff.seconds > 60:
                        rel_time = f"{diff.seconds // 60}m ago"
                        
                action_map = {
                    "hr": f"Processed candidate profile",
                    "invoices": f"Processed vendor invoice",
                    "invoice": f"Processed vendor invoice",
                    "meetings": f"Summarized meeting",
                    "meeting": f"Summarized meeting",
                    "approvals": f"Approval requested",
                    "approval": f"Approval requested"
                }
                
                recent_activity.append({
                    "action": action_map.get(module, f"Executed {module.capitalize()} automation"),
                    "details": f"Status: {status.capitalize()}",
                    "time": rel_time,
                    "type": module
                })
                
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch status metrics: {exc}") from exc
    finally:
        conn.close()

    # System status
    system_status = "degraded"
    n8n_base = os.getenv("N8N_BASE_URL", "https://n8n-production-8c140.up.railway.app")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{n8n_base.rstrip('/')}/healthz")
            if resp.status_code == 200:
                system_status = "active"
            else:
                # fallback check if healthz is not enabled
                resp = await client.get(f"{n8n_base.rstrip('/')}/api/v1/workflows")
                if resp.status_code in (200, 401):
                    system_status = "active"
    except Exception:
        pass

    return {
        "user_email": user_email,
        "invoices_processed": invoices_processed,
        "meetings_summarized": meetings_summarized,
        "pending_approvals": pending_approvals,
        "system_status": system_status,
        "recent_activity": recent_activity,
    }
