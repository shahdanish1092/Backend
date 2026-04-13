import os
import json
from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute(
    '''
    SELECT user_email, id::text, module, status, updated_at, output_summary
    FROM execution_logs
    ORDER BY updated_at DESC
    LIMIT 20
    '''
)
rows = cur.fetchall()
results = []
for row in rows:
    results.append({
        'user_email': row[0],
        'request_id': row[1],
        'module': row[2],
        'status': row[3],
        'updated_at': row[4].isoformat() if row[4] else None,
        'output_summary': row[5] or {}
    })
print(json.dumps(results, default=str, indent=2))
cur.close()
conn.close()
