import os
from fastapi import Header, HTTPException

def get_current_user(x_user_email: str | None = Header(None)):
    """
    Reads X-User-Email header sent by the frontend axios interceptor.
    For protected routes, validates the email exists in users table.
    """
    if not x_user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # defer import of supabase client until needed to avoid import-time issues
    from database import get_supabase

    sb = get_supabase()
    try:
        result = sb.table("users").select("email,full_name").eq("email", x_user_email).single().execute()
    except Exception:
        raise HTTPException(status_code=500, detail="User lookup failed")

    if not result.data:
        raise HTTPException(status_code=401, detail="User not found")

    return result.data
