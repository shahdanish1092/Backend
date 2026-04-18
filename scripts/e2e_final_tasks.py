import sys
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_hr_domain():
    print("\n--- Test 1: HR Domain ---")
    payload = {
        "text": "Review this job application for a Python developer with FastAPI experience",
        "active_connectors": ["gmail", "calendar"],
        "user_email": "danishshah9749@gmail.com"
    }
    resp = client.post("/api/chat/message", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")

def test_invoice_domain():
    print("\n--- Test 2: Invoice Domain ---")
    payload = {
        "user_email": "danishshah9749@gmail.com",
        "file_base64": "JVBERi0xLjQKJSheetS0xIDEgMCBvYmoKPDwKL1R5cGUgL0NhdGEK...",
        "filename": "test_invoice.pdf"
    }
    resp = client.post("/api/webhooks/invoice/trigger", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")

def test_meeting_domain():
    print("\n--- Test 3: Meeting Domain ---")
    payload = {
        "text": "Summarize our product roadmap meeting, attendees were Sarah and John",
        "active_connectors": ["calendar"],
        "user_email": "danishshah9749@gmail.com"
    }
    resp = client.post("/api/chat/message", json=payload)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")

def test_connector_status():
    print("\n--- Test 4: Connector Status ---")
    headers = {"X-User-Email": "danishshah9749@gmail.com"}
    resp = client.get("/api/connectors", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}")

if __name__ == "__main__":
    test_hr_domain()
    test_invoice_domain()
    test_meeting_domain()
    test_connector_status()
