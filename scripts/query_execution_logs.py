import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()
import psycopg2

email = sys.argv[1] if len(sys.argv) > 1 else None
if not email:
    print(json.dumps({"error":"email required"}))
    sys.exit(1)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute(
    """
    SELECT id::text, module, status, created_at, updated_at, output_summary
    FROM execution_logs
    WHERE user_email = %s
    ORDER BY updated_at DESC, created_at DESC
    LIMIT 10
    """,
    (email,)
)
rows = cur.fetchall()
results = []
for row in rows:
    results.append({
        "request_id": row[0],
        "module": row[1],
        "status": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
        "updated_at": row[4].isoformat() if row[4] else None,
        "output_summary": row[5] or {},
    })
print(json.dumps(results, default=str))
cur.close()
conn.close()
