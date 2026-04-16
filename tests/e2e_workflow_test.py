import os
import time
import requests

BACKEND = os.getenv("BACKEND_PUBLIC_URL") or os.getenv("FASTAPI_BASE_URL") or "http://127.0.0.1:8000"
BACKEND = BACKEND.rstrip('/')
USER_EMAIL = os.getenv("E2E_USER_EMAIL", "e2e-n8n@example.com")


def test_e2e_workflow_run():
    payload = {"text": "E2E test: shortlist candidate", "active_connectors": [], "user_email": USER_EMAIL}
    print("Triggering backend chat endpoint at", BACKEND + "/api/chat/message")
    r = requests.post(BACKEND + "/api/chat/message", json=payload, timeout=10)
    if r.status_code != 200:
        print("Trigger failed", r.status_code, r.text)
        raise AssertionError("Trigger failed")
    data = r.json()
    execution_id = data.get("execution_id") or data.get("request_id")
    if not execution_id:
        print("No execution id returned", data)
        raise AssertionError("No execution id returned")

    print("Execution id:", execution_id)

    # wait and poll
    deadline = time.time() + 60
    while time.time() < deadline:
        time.sleep(5)
        try:
            er = requests.get(BACKEND + f"/api/executions/{execution_id}", headers={"X-User-Email": USER_EMAIL}, timeout=10)
        except Exception as exc:
            print("Error polling execution", exc)
            continue
        if er.status_code == 404:
            print("Execution not yet created (404). Retrying...")
            continue
        if er.status_code == 403:
            print("Forbidden when polling execution. Check X-User-Email header.")
            raise AssertionError("Forbidden when polling execution")
        if er.status_code != 200:
            print("Unexpected status polling execution", er.status_code, er.text)
            continue
        payload = er.json()
        status = payload.get("status")
        print("Polled status:", status)
        if status in {"completed", "failed", "timeout"}:
            if status == "completed":
                print("PASS: execution completed", payload)
                return
            else:
                print("FAIL: execution in terminal state", status, payload)
                raise AssertionError(f"Execution ended with status {status}")

    print("Timed out waiting for execution to complete")
    raise AssertionError("Timed out waiting for execution to complete")
