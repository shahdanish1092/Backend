from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
import os
import urllib.parse
import httpx
import json
from database import get_db_connection

router = APIRouter()


@router.get("/google")
async def google_auth():
    """Builds Google auth URL and redirects user to accounts.google.com."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is missing in Backend Variables")
    if not redirect_uri:
        raise HTTPException(status_code=500, detail="GOOGLE_REDIRECT_URI is missing in Backend Variables")

    scope = "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events"
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(request: Request):
    """Exchanges code for tokens, fetches userinfo, upserts into users and google_tokens, then redirects to frontend."""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID missing")
    if not client_secret:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_SECRET missing")
    if not redirect_uri:
        raise HTTPException(status_code=500, detail="GOOGLE_REDIRECT_URI missing")

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data, timeout=20.0)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {resp.text}")
    token_response = resp.json()
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in")

    # Get userinfo
    async with httpx.AsyncClient() as client:
        ui = await client.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"}, timeout=10.0)
    if ui.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch userinfo")
    userinfo = ui.json()
    email = userinfo.get("email")
    name = userinfo.get("name")
    picture = userinfo.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google did not return an email")

    # Upsert user and tokens into Postgres via psycopg2
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (email, full_name, picture, last_login)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name, picture = EXCLUDED.picture, last_login = now()
            RETURNING email
            """,
            (email, name, picture),
        )
        # upsert google_tokens
        cur.execute(
            """
            INSERT INTO google_tokens (user_email, access_token, refresh_token, token_expiry, scopes, created_at, updated_at)
            VALUES (%s, %s, %s, now() + (interval '%s seconds'), %s, now(), now())
            ON CONFLICT (user_email) DO UPDATE SET access_token = EXCLUDED.access_token, refresh_token = EXCLUDED.refresh_token, token_expiry = EXCLUDED.token_expiry, scopes = EXCLUDED.scopes, updated_at = now()
            """,
            (email, access_token, refresh_token, expires_in or 0, token_response.get("scope", "").split()),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()

    frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
    redirect_to = f"{frontend.rstrip('/')}/dashboard?user_email={urllib.parse.quote(email)}&auth=success"
    return RedirectResponse(redirect_to)

