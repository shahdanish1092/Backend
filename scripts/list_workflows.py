#!/usr/bin/env python3
import os
import psycopg2

db = os.environ.get("DATABASE_URL")
if not db:
    raise RuntimeError("DATABASE_URL must be set")

conn = psycopg2.connect(db)
cur = conn.cursor()
cur.execute("SELECT id, n8n_id, name, domain, active, is_archived, created_at FROM workflows ORDER BY created_at DESC")
rows = cur.fetchall()
for r in rows:
    print(r)
cur.close()
conn.close()
