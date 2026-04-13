import os
import time
from uuid import uuid4

import pytest
import requests


API_BASE_URL = os.getenv("OFFICE_AUTOMATION_TEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL")


def _require_live_backend():
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=3)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(f"Live backend not available at {API_BASE_URL}: {exc}")


def _fetch_execution_log(request_id: str):
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is required for the live triage integration test")

    import psycopg2

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, status, output_summary
                FROM execution_logs
                WHERE id = %s
                """,
                (request_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


@pytest.mark.integration
def test_triage_flow_live():
    _require_live_backend()

    payload = {
        "user_email": f"triage-run-{uuid4().hex}@example.com",
        "category": "Recruitment",
        "email_data": {
            "subject": "Test",
            "body": "candidate body",
            "from": "applicant@example.com",
            "attachments": [],
        },
    }

    response = requests.post(f"{API_BASE_URL}/api/internal/triage", json=payload, timeout=20)
    assert response.status_code == 200

    body = response.json()
    assert body["request_id"]
    assert body["status"] in {"triggered", "failed_to_trigger"}
    assert body["workflow"] == "hr_recruitment"

    row = _fetch_execution_log(body["request_id"])
    assert row is not None
    assert row[0] == body["request_id"]
    assert row[1] in {"running", "failed_to_trigger", "triggering", "ranked", "shortlisted", "completed"}

    if os.getenv("N8N_API_KEY") and body["status"] == "triggered":
        deadline = time.time() + 30
        while time.time() < deadline:
            n8n_response = requests.get(f"{API_BASE_URL}/api/internal/n8n/executions/{body['request_id']}", timeout=10)
            if n8n_response.status_code == 200:
                execution_data = n8n_response.json()
                if execution_data.get("count", 0) > 0:
                    assert execution_data["matches"]
                    return
            elif n8n_response.status_code >= 500:
                pytest.skip(f"n8n execution lookup unavailable: {n8n_response.text}")
            time.sleep(2)

        pytest.fail("Timed out waiting for n8n execution to appear for request_id")
