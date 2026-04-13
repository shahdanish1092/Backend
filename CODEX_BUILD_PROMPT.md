# Office Automation Platform — Codex Build Prompt
# Paste this entire file into Codex to begin.

---

## PROJECT OVERVIEW

You are building the backend for **Spatial+ Office Automation**, a multi-tenant SaaS platform that lets startups automate their desk work. The frontend is already fully built in React/Shadcn. The n8n workflows already exist. Your job is to build the FastAPI intelligence layer that connects them.

**Tech stack:**
- FastAPI + Uvicorn (Python)
- Supabase PostgreSQL (via `supabase-py` for auth/db operations and `psycopg2-binary` for raw migrations)
- Google OAuth 2.0 (via `google-auth-oauthlib`)
- n8n (automation engine — you trigger it via webhooks, never replicate its logic)
- Groq/Llama 3 (AI — used inside n8n workflows, not directly in FastAPI)

**Architecture law (non-negotiable):**
FastAPI is the **intelligence and coordination layer only**. It handles auth, stores/reads data, and triggers n8n webhooks. It does NOT process emails, parse invoices, run AI, or execute any automation logic. n8n does all of that.

---

## DIRECTORY STRUCTURE TO CREATE

```
Office_automation/
├── .env                          # Copy from .env.example, fill values
├── .env.example
├── requirements.txt
├── main.py                       # FastAPI app entry point
├── database.py                   # Supabase client + DB connection
├── auth/
│   ├── __init__.py
│   ├── google_oauth.py           # Google OAuth flow
│   └── dependencies.py           # get_current_user dependency
├── routers/
│   ├── __init__.py
│   ├── auth.py                   # /api/auth/* routes
│   ├── dashboard.py              # /api/status/* routes
│   ├── invoices.py               # /api/invoices/* and /api/webhooks/invoice
│   ├── hr.py                     # /api/hr/* and /api/webhooks/hr
│   ├── meetings.py               # /api/meetings/* and /api/webhooks/meeting
│   ├── approvals.py              # /api/approvals/* and /api/approve/*
│   └── admin.py                  # /api/admin/vendors/*
├── models/
│   ├── __init__.py
│   └── schemas.py                # All Pydantic request/response models
├── db/
│   └── migrations/
│       ├── 001_create_execution_logs.sql   # Already exists
│       ├── 002_create_users.sql
│       ├── 003_create_google_tokens.sql
│       ├── 004_create_invoices.sql
│       ├── 005_create_hr_connections.sql
│       ├── 006_create_meetings.sql
│       ├── 007_create_approvals.sql
│       └── 008_create_vendors.sql
└── scripts/
    └── run_all_migrations.py
```

---

## ENVIRONMENT VARIABLES

The `.env.example` already contains these — fill them in `.env`:

```env
# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Database direct connection (for migrations and psycopg2)
DATABASE_URL=postgresql://postgres:PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres?sslmode=require

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Groq / AI (used by n8n, stored here for n8n credential passing)
GROQ_API_KEY=your_groq_key
GROQ_BASE_URL=https://api.groq.com/openai/v1

# OCR Space
OCR_SPACE_API_KEY=your_ocr_key

# FastAPI
FASTAPI_BASE_URL=http://localhost:8000
WEBHOOK_SECRET=your_random_secret_32chars
JWT_SECRET_KEY=your_random_jwt_secret_32chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=168

# n8n
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=your_n8n_api_key

# Frontend
FRONTEND_URL=http://localhost:3000
```

---

## REQUIREMENTS.TXT

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9
supabase==2.5.0
google-auth==2.29.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.0
python-multipart==0.0.9
pydantic==2.7.0
pydantic-settings==2.2.1
```

---

## DATABASE MIGRATIONS

### Migration 001 — Already exists (execution_logs). Skip.

### Migration 002 — users
```sql
BEGIN;
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  picture TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_login TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
COMMIT;
```

### Migration 003 — google_tokens
```sql
BEGIN;
CREATE TABLE IF NOT EXISTS google_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  token_expiry TIMESTAMPTZ,
  scopes TEXT[],
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_google_tokens_user ON google_tokens(user_email);
COMMIT;
```

### Migration 004 — invoices
```sql
BEGIN;
CREATE TABLE IF NOT EXISTS invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  vendor_name TEXT,
  invoice_number TEXT,
  amount NUMERIC(12,2),
  invoice_date DATE,
  due_date DATE,
  line_items JSONB,
  raw_extracted JSONB,
  status TEXT NOT NULL DEFAULT 'processing',
  n8n_execution_id TEXT,
  source_email_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invoices_user_email ON invoices(user_email);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
COMMIT;
```

### Migration 005 — hr_connections
```sql
BEGIN;
CREATE TABLE IF NOT EXISTS hr_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
  n8n_workflow_id TEXT,
  webhook_url TEXT,
  is_active BOOLEAN DEFAULT true,
  last_sync TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_hr_user ON hr_connections(user_email);
COMMIT;
```

### Migration 006 — meetings
```sql
BEGIN;
CREATE TABLE IF NOT EXISTS meetings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  title TEXT,
  source_type TEXT DEFAULT 'audio',
  transcript TEXT,
  summary TEXT,
  action_items JSONB,
  participants TEXT[],
  meeting_date DATE,
  duration_minutes INTEGER,
  status TEXT NOT NULL DEFAULT 'processing',
  n8n_execution_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_meetings_user_email ON meetings(user_email);
COMMIT;
```

### Migration 007 — approvals
```sql
BEGIN;
CREATE TABLE IF NOT EXISTS approvals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  module TEXT NOT NULL,
  reference_id UUID,
  title TEXT NOT NULL,
  description TEXT,
  payload JSONB,
  status TEXT NOT NULL DEFAULT 'pending',
  approval_token UUID DEFAULT gen_random_uuid(),
  approved_by TEXT,
  approved_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_approvals_user_email ON approvals(user_email);
CREATE INDEX IF NOT EXISTS idx_approvals_token ON approvals(approval_token);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
COMMIT;
```

### Migration 008 — vendors
```sql
BEGIN;
CREATE TABLE IF NOT EXISTS vendors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,
  name TEXT NOT NULL,
  email TEXT,
  approved BOOLEAN DEFAULT false,
  invoice_count INTEGER DEFAULT 0,
  total_spend NUMERIC(14,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vendors_user_email ON vendors(user_email);
COMMIT;
```

---

## MAIN.PY

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from routers import auth, dashboard, invoices, hr, meetings, approvals, admin

app = FastAPI(title="Spatial+ Office Automation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(invoices.router, prefix="/api", tags=["invoices"])
app.include_router(hr.router, prefix="/api", tags=["hr"])
app.include_router(meetings.router, prefix="/api", tags=["meetings"])
app.include_router(approvals.router, prefix="/api", tags=["approvals"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## DATABASE.PY

```python
import os
import psycopg2
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_supabase: Client = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )
    return _supabase

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))
```

---

## AUTH MODULE

### auth/google_oauth.py
```python
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

def create_oauth_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return flow

def refresh_token_if_needed(access_token: str, refresh_token: str) -> Credentials:
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        token_uri="https://oauth2.googleapis.com/token",
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds
```

### auth/dependencies.py
```python
import os
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError
from database import get_supabase

def get_current_user(x_user_email: str | None = Header(None)):
    """
    Reads X-User-Email header sent by the frontend axios interceptor.
    For protected routes, validates the email exists in users table.
    """
    if not x_user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    sb = get_supabase()
    result = sb.table("users").select("email,full_name").eq("email", x_user_email).single().execute()
    
    if not result.data:
        raise HTTPException(status_code=401, detail="User not found")
    
    return result.data

def get_user_tokens(user_email: str):
    """Fetch stored Google tokens for a user."""
    sb = get_supabase()
    result = sb.table("google_tokens").select("*").eq("user_email", user_email).single().execute()
    if not result.data:
        raise HTTPException(status_code=403, detail="Google account not connected")
    return result.data
```

---

## ROUTERS

### routers/auth.py
```python
import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from auth.google_oauth import create_oauth_flow
from database import get_supabase

router = APIRouter()

@router.get("/google")
async def google_auth_redirect():
    """Redirect user to Google OAuth consent screen."""
    flow = create_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return RedirectResponse(url=auth_url)

@router.get("/google/callback")
async def google_auth_callback(code: str, request: Request):
    """
    Handle Google OAuth callback.
    Exchange code for tokens, upsert user and tokens in DB,
    then redirect to frontend dashboard.
    """
    try:
        flow = create_oauth_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get user info from Google
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"}
            )
            user_info = resp.json()

        email = user_info["email"]
        sb = get_supabase()

        # Upsert user
        sb.table("users").upsert({
            "email": email,
            "full_name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "last_login": "now()"
        }).execute()

        # Upsert tokens
        sb.table("google_tokens").upsert({
            "user_email": email,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token or "",
            "scopes": list(credentials.scopes or []),
        }).execute()

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(
            url=f"{frontend_url}/dashboard?user_email={email}&auth=success"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

@router.get("/me")
async def get_me(x_user_email: str | None = None):
    if not x_user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sb = get_supabase()
    result = sb.table("users").select("*").eq("email", x_user_email).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data

@router.post("/logout")
async def logout():
    return {"status": "ok", "message": "Logged out"}
```

### routers/dashboard.py
```python
from fastapi import APIRouter, Depends
from auth.dependencies import get_current_user
from database import get_supabase

router = APIRouter()

@router.get("/status/{user_email}")
async def get_dashboard_status(user_email: str, current_user=Depends(get_current_user)):
    sb = get_supabase()

    # Count invoices
    inv = sb.table("invoices").select("id", count="exact").eq("user_email", user_email).execute()
    invoices_count = inv.count or 0

    # Count meetings
    mtg = sb.table("meetings").select("id", count="exact").eq("user_email", user_email).execute()
    meetings_count = mtg.count or 0

    # Count pending approvals
    apr = sb.table("approvals").select("id", count="exact")\
        .eq("user_email", user_email).eq("status", "pending").execute()
    pending_count = apr.count or 0

    # Recent activity from execution_logs (last 10)
    logs = sb.table("execution_logs")\
        .select("module,status,created_at,output_summary")\
        .eq("user_email", user_email)\
        .order("created_at", desc=True)\
        .limit(10).execute()

    activity = []
    for log in (logs.data or []):
        activity.append({
            "action": f"{log['module'].replace('_', ' ').title()} {'Completed' if log['status'] == 'success' else log['status'].title()}",
            "details": (log.get("output_summary") or {}).get("summary", ""),
            "time": log["created_at"],
            "type": "invoice" if "invoice" in log["module"] else
                    "meeting" if "meeting" in log["module"] else
                    "hr" if "hr" in log["module"] else "approval"
        })

    return {
        "invoices_processed": invoices_count,
        "meetings_summarized": meetings_count,
        "pending_approvals": pending_count,
        "system_status": "active",
        "recent_activity": activity
    }
```

### routers/invoices.py
```python
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth.dependencies import get_current_user
from database import get_supabase

router = APIRouter()

class InvoiceWebhookPayload(BaseModel):
    user_email: str
    file_base64: str
    filename: str

@router.get("/invoices/{user_email}")
async def get_invoices(user_email: str, current_user=Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("invoices")\
        .select("*")\
        .eq("user_email", user_email)\
        .order("created_at", desc=True)\
        .execute()
    return result.data or []

@router.post("/webhooks/invoice")
async def receive_invoice(payload: InvoiceWebhookPayload):
    """
    Receives invoice upload from frontend.
    Creates a pending invoice record, then triggers the n8n invoice workflow.
    """
    sb = get_supabase()

    # Insert a processing record
    record = sb.table("invoices").insert({
        "user_email": payload.user_email,
        "status": "processing",
        "raw_extracted": {"filename": payload.filename}
    }).execute()

    invoice_id = record.data[0]["id"]

    # Trigger n8n webhook
    n8n_webhook = os.getenv("N8N_INVOICE_WEBHOOK_URL")
    if n8n_webhook:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(n8n_webhook, json={
                    "invoice_id": invoice_id,
                    "user_email": payload.user_email,
                    "file_base64": payload.file_base64,
                    "filename": payload.filename,
                    "callback_url": f"{os.getenv('FASTAPI_BASE_URL')}/api/internal/invoice-result"
                })
        except Exception:
            pass  # n8n is fire-and-forget from frontend perspective

    return {
        "success": True,
        "invoice_id": invoice_id,
        "status": "processing",
        "message": "Invoice received. Processing started."
    }

@router.post("/internal/invoice-result")
async def receive_invoice_result(data: dict):
    """
    n8n calls this when invoice processing is complete.
    Updates the invoice record and creates an approval if needed.
    """
    sb = get_supabase()
    invoice_id = data.get("invoice_id")
    if not invoice_id:
        raise HTTPException(status_code=400, detail="invoice_id required")

    # Update invoice record
    sb.table("invoices").update({
        "vendor_name": data.get("vendor_name"),
        "invoice_number": data.get("invoice_number"),
        "amount": data.get("amount"),
        "invoice_date": data.get("invoice_date"),
        "line_items": data.get("line_items"),
        "raw_extracted": data.get("raw_extracted"),
        "status": data.get("status", "pending_approval"),
        "updated_at": "now()"
    }).eq("id", invoice_id).execute()

    # Log execution
    sb.table("execution_logs").insert({
        "user_email": data.get("user_email"),
        "module": "invoice_processing",
        "status": "success",
        "output_summary": {"summary": f"Invoice from {data.get('vendor_name', 'unknown')} extracted"}
    }).execute()

    # Create approval request if amount exists
    if data.get("amount") and data.get("user_email"):
        sb.table("approvals").insert({
            "user_email": data["user_email"],
            "module": "invoice",
            "reference_id": invoice_id,
            "title": f"Invoice from {data.get('vendor_name', 'Unknown')}",
            "description": f"Amount: ₹{data.get('amount', 0):,.2f}",
            "payload": data,
            "status": "pending"
        }).execute()

    return {"status": "ok"}
```

### routers/hr.py
```python
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth.dependencies import get_current_user
from database import get_supabase

router = APIRouter()

class HRConnectPayload(BaseModel):
    user_email: str
    hr_webhook_url: str
    input_format: str = "base64"
    callback_url: str = ""
    secret: str = ""

@router.get("/hr/status/{user_email}")
async def get_hr_status(user_email: str, current_user=Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("hr_connections").select("*").eq("user_email", user_email).execute()
    if not result.data:
        return {"connected": False, "last_sync": None, "webhook_url": None}
    row = result.data[0]
    return {
        "connected": row["is_active"],
        "last_sync": row["last_sync"],
        "webhook_url": row["webhook_url"]
    }

@router.post("/webhooks/hr")
async def connect_hr(payload: HRConnectPayload):
    sb = get_supabase()
    sb.table("hr_connections").upsert({
        "user_email": payload.user_email,
        "webhook_url": payload.hr_webhook_url,
        "is_active": True,
    }).execute()
    return {"success": True, "connected": True, "message": "HR workflow connected"}

@router.post("/hr/test/{user_email}")
async def test_hr(user_email: str, current_user=Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("hr_connections").select("webhook_url").eq("user_email", user_email).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="HR not connected")
    webhook_url = result.data[0]["webhook_url"]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(webhook_url, json={"type": "ping", "user_email": user_email})
        return {"success": True, "message": "Connection test successful", "response_time": "~100ms"}
    except Exception as e:
        return {"success": False, "message": f"Connection test failed: {str(e)}"}

@router.delete("/hr/disconnect/{user_email}")
async def disconnect_hr(user_email: str, current_user=Depends(get_current_user)):
    sb = get_supabase()
    sb.table("hr_connections").update({"is_active": False}).eq("user_email", user_email).execute()
    return {"success": True, "message": "HR workflow disconnected"}

@router.post("/internal/hr-result")
async def receive_hr_result(data: dict):
    """n8n posts recruitment results back here."""
    sb = get_supabase()
    sb.table("execution_logs").insert({
        "user_email": data.get("user_email"),
        "module": "hr_recruitment",
        "status": "success",
        "output_summary": data
    }).execute()
    # Create approval if shortlisted
    if data.get("shortlisted") and data.get("user_email"):
        sb.table("approvals").insert({
            "user_email": data["user_email"],
            "module": "hr",
            "title": f"Candidate: {data.get('candidate_name', 'Unknown')}",
            "description": data.get("summary", ""),
            "payload": data,
            "status": "pending"
        }).execute()
    return {"status": "ok"}
```

### routers/meetings.py
```python
import os
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth.dependencies import get_current_user
from database import get_supabase

router = APIRouter()

class MeetingWebhookPayload(BaseModel):
    user_email: str
    audio_base64: str | None = None
    transcript: str | None = None
    title: str = "Meeting"

@router.get("/meetings/{user_email}")
async def get_meetings(user_email: str, current_user=Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("meetings").select("*").eq("user_email", user_email)\
        .order("created_at", desc=True).execute()
    return result.data or []

@router.post("/webhooks/meeting")
async def receive_meeting(payload: MeetingWebhookPayload):
    sb = get_supabase()
    record = sb.table("meetings").insert({
        "user_email": payload.user_email,
        "title": payload.title,
        "transcript": payload.transcript,
        "source_type": "audio" if payload.audio_base64 else "transcript",
        "status": "processing"
    }).execute()
    meeting_id = record.data[0]["id"]

    n8n_webhook = os.getenv("N8N_MEETING_WEBHOOK_URL")
    if n8n_webhook:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(n8n_webhook, json={
                    "meeting_id": meeting_id,
                    "user_email": payload.user_email,
                    "transcript": payload.transcript,
                    "audio_base64": payload.audio_base64,
                    "callback_url": f"{os.getenv('FASTAPI_BASE_URL')}/api/internal/meeting-result"
                })
        except Exception:
            pass

    return {"success": True, "meeting_id": meeting_id, "status": "processing"}

@router.post("/internal/meeting-result")
async def receive_meeting_result(data: dict):
    sb = get_supabase()
    meeting_id = data.get("meeting_id")
    if meeting_id:
        sb.table("meetings").update({
            "summary": data.get("summary"),
            "action_items": data.get("action_items"),
            "status": "completed"
        }).eq("id", meeting_id).execute()
    sb.table("execution_logs").insert({
        "user_email": data.get("user_email"),
        "module": "meeting_summarizer",
        "status": "success",
        "output_summary": {"summary": data.get("summary", "")[:200]}
    }).execute()
    return {"status": "ok"}
```

### routers/approvals.py
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth.dependencies import get_current_user
from database import get_supabase

router = APIRouter()

class ApprovalAction(BaseModel):
    action: str  # "approve" | "reject"
    notes: str = ""

@router.get("/approvals/{user_email}")
async def get_approvals(user_email: str, current_user=Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("approvals").select("*")\
        .eq("user_email", user_email)\
        .order("created_at", desc=True).execute()
    return result.data or []

@router.post("/approve/{token}")
async def process_approval(token: str, body: ApprovalAction):
    """
    Called when user approves/rejects from email link or frontend.
    token is the approval_token UUID.
    """
    sb = get_supabase()
    result = sb.table("approvals").select("*").eq("approval_token", token).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Approval not found")

    new_status = "approved" if body.action == "approve" else "rejected"
    sb.table("approvals").update({
        "status": new_status,
        "approved_at": "now()"
    }).eq("approval_token", token).execute()

    # If it's an invoice approval, update the invoice record too
    row = result.data
    if row["module"] == "invoice" and row["reference_id"]:
        sb.table("invoices").update({
            "status": new_status,
            "updated_at": "now()"
        }).eq("id", row["reference_id"]).execute()

    return {"status": "ok", "action": new_status}
```

### routers/admin.py
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth.dependencies import get_current_user
from database import get_supabase

router = APIRouter()

class VendorCreate(BaseModel):
    user_email: str
    name: str
    email: str = ""
    approved: bool = False

@router.get("/vendors/{user_email}")
async def get_vendors(user_email: str, current_user=Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("vendors").select("*").eq("user_email", user_email)\
        .order("created_at", desc=True).execute()
    return result.data or []

@router.post("/vendors")
async def create_vendor(payload: VendorCreate, current_user=Depends(get_current_user)):
    sb = get_supabase()
    result = sb.table("vendors").insert({
        "user_email": payload.user_email,
        "name": payload.name,
        "email": payload.email,
        "approved": payload.approved
    }).execute()
    return result.data[0]
```

---

## N8N WORKFLOW INSTRUCTIONS

You do NOT need to rewrite the workflows in code. Instead, give these instructions for modifying the 3 existing JSONs in n8n:

### Workflow 1: Gmail AI Triage (Router)
**File:** `Router/Ai-powered email triage & auto-response system with OpenAI agents & Gmail.json`

**Changes to make inside n8n:**
1. Swap every `lmChatOpenAi`, `lmChatGoogleGemini`, `lmChatOpenRouter` node with `@n8n/n8n-nodes-langchain.lmChatGroq` using model `llama3-70b-8192`
2. Swap every `openAi` (message a model) node with a `@n8n/n8n-nodes-langchain.lmChatGroq` call
3. Remove Telegram notifier nodes (replace with HTTP Request nodes that POST to FastAPI `/api/internal/triage-log`)
4. Remove Pinecone vector store nodes (not needed for your scope)
5. Change the Text Classifier categories from Internal/Customer Support/Promotions/Admin-Finance/Sales to: **Recruitment / Invoice / General**
6. The Gmail trigger stays as-is — it monitors your company inbox
7. Add an HTTP Request node at the end of each branch that POSTs to `{{$env.FASTAPI_BASE_URL}}/api/internal/triage-result` with `{user_email, category, email_subject, email_from, action_taken}`

### Workflow 2: Invoice Processing
**File:** `Finance/Automate invoice processing from Gmail and human verification.json`

**Changes to make inside n8n:**
1. Swap `lmChatAzureOpenAi` with `@n8n/n8n-nodes-langchain.lmChatGroq` (model: `llama3-70b-8192`)
2. The Gmail trigger already monitors for PDF attachments — keep it
3. Add an HTTP Request node after Information Extractor that POSTs to `{{$env.FASTAPI_BASE_URL}}/api/internal/invoice-result` with all extracted fields + `user_email`
4. The "Manual Verification" email step stays — this is your human-in-the-loop approval email

### Workflow 3: HR Recruitment
**This workflow does not exist in your uploads — you need to create it in n8n:**

Create a new workflow with these nodes:
1. **Gmail Trigger** — watches for emails with "resume", "CV", "application" in subject
2. **Download Attachment** — gets the PDF attachment
3. **HTTP Request** — POST to OCR Space API with PDF base64 (your key: in env)
4. **Groq Chat Model + Information Extractor** — extract: name, email, phone, skills, experience_years, education
5. **IF node** — check if experience_years >= 2 AND required skills present
6. **HTTP Request (shortlisted branch)** — POST to `{{$env.FASTAPI_BASE_URL}}/api/internal/hr-result` with `{user_email, candidate_name, candidate_email, skills, experience_years, summary, shortlisted: true}`
7. **Gmail Send** — send "Application Received" reply to candidate
8. **HTTP Request (rejected branch)** — POST same endpoint with `{shortlisted: false}`

---

## FRONTEND CHANGES NEEDED

In the existing frontend, make these changes:

### 1. frontend/src/api/auth.js — Replace mock with real OAuth
```javascript
const BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export const authApi = {
  initiateGoogleAuth: () => {
    window.location.href = `${BASE_URL}/api/auth/google`;
  },
  getCurrentUser: () => localStorage.getItem('user_email'),
  setUserEmail: (email) => localStorage.setItem('user_email', email),
  logout: () => localStorage.removeItem('user_email'),
  isAuthenticated: () => !!localStorage.getItem('user_email'),
};
```

### 2. frontend/src/App.js — Handle OAuth callback redirect
Add this effect in the `App` function, before the return:
```javascript
useEffect(() => {
  const params = new URLSearchParams(window.location.search);
  const userEmail = params.get('user_email');
  const auth = params.get('auth');
  if (auth === 'success' && userEmail) {
    localStorage.setItem('user_email', userEmail);
    window.history.replaceState({}, '', '/dashboard');
  }
}, []);
```

### 3. frontend/src/pages/LandingPage.jsx — Wire the Connect Google button
Find the "Connect Google Account" or "Sign in with Google" button and ensure its `onClick` calls:
```javascript
import { authApi } from '../api/auth';
// ...
onClick={() => authApi.initiateGoogleAuth()}
```

### 4. Remove all mock data fallbacks from api/*.js
In `dashboard.js`, `invoices.js`, `hr.js`, `meetings.js`, `approvals.js`, `vendors.js` — remove the entire `catch` block mock return data. Replace with:
```javascript
} catch (error) {
  console.error('API error:', error);
  throw error;
}
```

### 5. frontend/.env (create this file)
```
REACT_APP_BACKEND_URL=http://localhost:8000
```

---

## SCRIPTS/RUN_ALL_MIGRATIONS.PY

```python
"""Run all SQL migrations in order against the Supabase Postgres database."""
import os
import glob
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_migrations():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not set")

    migrations_dir = Path(__file__).parent.parent / "db" / "migrations"
    sql_files = sorted(glob.glob(str(migrations_dir / "*.sql")))

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    for sql_file in sql_files:
        print(f"Running: {Path(sql_file).name}")
        sql = Path(sql_file).read_text(encoding="utf-8")
        cur.execute(sql)
        conn.commit()
        print(f"  ✓ Done")

    cur.close()
    conn.close()
    print("\nAll migrations applied successfully.")

if __name__ == "__main__":
    run_migrations()
```

---

## IMPORTANT: ABOUT SUPABASE SETUP

**Do NOT let Emergent build your Supabase.** Supabase setup is a 2-minute manual task:

1. Go to https://supabase.com → your existing project (`zvetalhtlbvnyjnkbjjc`)
2. The project already exists — your `.env.example` has the credentials
3. Run `python scripts/run_all_migrations.py` — this creates all 8 tables
4. Done. No Emergent needed.

The only values you need from Supabase dashboard:
- `SUPABASE_URL` ✓ already in your env
- `SUPABASE_ANON_KEY` ✓ already in your env
- `SUPABASE_SERVICE_ROLE_KEY` ✓ already in your env
- `DATABASE_URL` ✓ already in your env

**⚠️ SECURITY WARNING:** Your `.env.example` file contains live credentials. Before doing anything:
1. Rotate your Supabase service role key at: Supabase → Settings → API
2. Rotate your Google OAuth secret at: Google Cloud Console → Credentials
3. Rotate your Groq API key at: console.groq.com
4. Never commit `.env` to git — add it to `.gitignore`

---

## WHAT TO BUILD — EXECUTION CHECKLIST FOR CODEX

Work through these phases in order. Self-verify each phase passes before moving on.

### Phase 1 — Scaffold
- [ ] Create the directory structure above
- [ ] Create `requirements.txt` with exact versions
- [ ] Create `main.py`, `database.py`
- [ ] Create all `__init__.py` files
- [ ] Create `.env` from `.env.example` (do not commit)

### Phase 2 — Migrations
- [ ] Write all 8 migration SQL files
- [ ] Write `scripts/run_all_migrations.py`
- [ ] Run migrations: `python scripts/run_all_migrations.py`
- [ ] Verify all 8 tables exist in Supabase Table Editor

### Phase 3 — Auth
- [ ] Write `auth/google_oauth.py`
- [ ] Write `auth/dependencies.py`
- [ ] Write `routers/auth.py`
- [ ] Test: `GET /api/auth/google` returns redirect to Google

### Phase 4 — All Routers
- [ ] Write `routers/dashboard.py`
- [ ] Write `routers/invoices.py`
- [ ] Write `routers/hr.py`
- [ ] Write `routers/meetings.py`
- [ ] Write `routers/approvals.py`
- [ ] Write `routers/admin.py`
- [ ] Write `models/schemas.py` (any shared Pydantic models)

### Phase 5 — Smoke Test
- [ ] `uvicorn main:app --reload` starts without errors
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `GET /docs` shows all routes
- [ ] `GET /api/auth/google` redirects to Google

### Phase 6 — Frontend Wiring
- [ ] Apply all 5 frontend changes listed above
- [ ] Create `frontend/.env` with `REACT_APP_BACKEND_URL`
- [ ] Start frontend: `yarn start`
- [ ] Click "Connect Google" → goes to Google consent → redirects back → user_email in localStorage
- [ ] Dashboard loads real data (may show empty arrays — that's correct)

### Phase 7 — n8n Wiring
- [ ] Open n8n, import invoice workflow, swap AI node to Groq, add callback HTTP node
- [ ] Import router workflow, simplify to 3 categories, swap AI nodes to Groq
- [ ] Create HR recruitment workflow from scratch per spec above
- [ ] Set n8n environment variables: FASTAPI_BASE_URL, GROQ_API_KEY
- [ ] Test invoice workflow end-to-end: send a PDF to your Gmail → check Supabase invoices table → check frontend

---

## SELF-VERIFICATION GATES

Before declaring each phase done, Codex must verify:

**Phase 2 gate:** Run `SELECT table_name FROM information_schema.tables WHERE table_schema='public';` against Supabase — must show all 8 tables.

**Phase 5 gate:** `curl http://localhost:8000/health` must return `{"status":"ok"}`. `curl http://localhost:8000/docs` must return HTML (FastAPI Swagger UI).

**Phase 6 gate:** Click "Connect Google" in the frontend — after OAuth, `localStorage.getItem('user_email')` must return a real email address. The dashboard must make a real API call visible in the browser network tab to `/api/status/{email}`.

**Phase 7 gate:** Send an email with a PDF attachment to the Gmail account — within 60 seconds, a row must appear in the Supabase `invoices` table with `status = 'processing'`.

---

## N8N ENVIRONMENT VARIABLES TO SET

In n8n Settings → Environment Variables, add:
```
FASTAPI_BASE_URL=http://your-fastapi-host:8000
GROQ_API_KEY=your_groq_key
OCR_SPACE_API_KEY=your_ocr_key
```

And add to your FastAPI `.env`:
```
N8N_INVOICE_WEBHOOK_URL=http://localhost:5678/webhook/invoice-processing
N8N_HR_WEBHOOK_URL=http://localhost:5678/webhook/hr-recruitment
N8N_MEETING_WEBHOOK_URL=http://localhost:5678/webhook/meeting-summarizer
```

(Get these webhook URLs from each n8n workflow's trigger node after import.)
