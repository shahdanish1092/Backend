#!/usr/bin/env python3
"""List workflows using the project's `database.get_db_connection()` so .env is loaded."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from database import get_db_connection

conn = get_db_connection()
try:
    with conn.cursor() as cur:
        cur.execute("SELECT id, n8n_id, name, domain, active, is_archived, created_at FROM workflows ORDER BY created_at DESC")
        rows = cur.fetchall()
    for r in rows:
        print(r)
finally:
    conn.close()
