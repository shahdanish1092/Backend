import os
import json
import requests
import psycopg2
from time import sleep

API = os.getenv("FASTAPI_BASE_URL", "http://localhost:8000")

payload = {
    "invoice_id": "00000000-0000-4000-8000-000000000001",
    "user_email": "test@example.com",
    "vendor_name": "ACME Corp",
    "invoice_number": "INV-1234",
    "amount": 1234.56,
    "invoice_date": "2026-04-01",
    "line_items": [{"desc": "Service", "qty": 1, "price": 1234.56}],
    "raw_extracted": {"text": "dummy"},
    "status": "processed"
}

resp = requests.post(f"{API}/api/internal/invoice-result", json=payload, timeout=10)
print("POST /api/internal/invoice-result ->", resp.status_code, resp.text)

# Wait briefly for DB writes to commit
sleep(0.5)

db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise SystemExit("DATABASE_URL not set")

conn = psycopg2.connect(db_url)
cur = conn.cursor()
cur.execute("SELECT id, user_email, amount, invoice_number FROM invoices WHERE id=%s", (payload["invoice_id"],))
inv = cur.fetchone()
print("Invoice row:", inv)
cur.execute("SELECT id, module, status, payload FROM approvals WHERE reference_id=%s OR payload->>\'invoice_id\'=%s", (payload["invoice_id"], payload["invoice_id"]))
appr = cur.fetchone()
print("Approval row:", appr)
cur.close()
conn.close()
