import sys
import json
import asyncio
from fastapi.testclient import TestClient
from main import app
from database import get_db_connection

client = TestClient(app)

def run_test():
    print("Sending E2E request to /api/chat/message...")
    resp = client.post(
        "/api/chat/message",
        json={
            "text": "I need to process a job application for a Python developer",
            "active_connectors": ["n8n"],
            "user_email": "shahdanish1092@gmail.com"
        }
    )
    
    print(f"Status Code: {resp.status_code}")
    data = resp.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if resp.status_code == 200 and "execution_id" in data and data["execution_id"]:
        exec_id = data["execution_id"]
        print(f"Checking database for execution_id {exec_id}...")
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT status, module FROM execution_logs WHERE id = %s", (exec_id,))
                row = cur.fetchone()
                if row:
                    print(f"DB Row found - Status: {row[0]}, Domain: {row[1]}")
                else:
                    print("DB Row not found!")
        finally:
            conn.close()

if __name__ == "__main__":
    run_test()
