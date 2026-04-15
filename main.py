from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

load_dotenv()

from routers import auth, dashboard, invoices, hr, meetings, approvals, admin, internal, hr_execute, chat, connectors


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

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
app.include_router(hr_execute.router, prefix="/api", tags=["hr_execute"])
app.include_router(meetings.router, prefix="/api", tags=["meetings"])
app.include_router(approvals.router, prefix="/api", tags=["approvals"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(internal.router, prefix="/api", tags=["internal"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(connectors.router, prefix="/api/connectors", tags=["connectors"])


@app.get("/health")
async def health():
    return {"status": "ok"}
