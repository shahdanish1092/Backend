import os
import time
import requests

import pytest

BACKEND = os.getenv("BACKEND_PUBLIC_URL") or os.getenv("FASTAPI_BASE_URL")
RUN_E2E = os.getenv("RUN_E2E", "0")
if not BACKEND and RUN_E2E != "1":
    pytest.skip("Skipping E2E test: set BACKEND_PUBLIC_URL or RUN_E2E=1 to enable", allow_module_level=True)

BACKEND = (BACKEND or "http://127.0.0.1:8000").rstrip('/')
USER_EMAIL = os.getenv("E2E_USER_EMAIL", "e2e-n8n@example.com")


def test_e2e_workflow_run():
    # Health check
    health_ok = False
    for path in ("/health", "/docs"):
        try:
            r = requests.get(BACKEND + path, timeout=10)
        except Exception:
            r = None
        if r and r.status_code == 200:
            health_ok = True
            break

    if not health_ok:
        print("Health check failed for", BACKEND)
        raise AssertionError("Health check failed")

    # Trigger workflow
    payload = {"text": "Test HR workflow", "active_connectors": [], "user_email": USER_EMAIL}
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

    # Wait & Poll (up to 30s)
    final_status = None
    final_payload = None
    deadline = time.time() + 30
    TERMINAL_STATES = {"success", "completed", "failed", "failed_to_trigger", "timeout"}
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
            print("Forbidden when polling execution. Check X-User-Email header and user_email used for trigger.")
            raise AssertionError("Forbidden when polling execution")
        if er.status_code != 200:
            print("Unexpected status polling execution", er.status_code, er.text)
            continue
        payload = er.json()
        status = (payload.get("status") or "").lower()
        print("Polled status:", status)
        if status in TERMINAL_STATES:
            final_status = status
            final_payload = payload
            break

    # Verify results
    overall_ok = True
    health_pass = True
    trigger_pass = True
    poll_pass = False
    result_pass = False

    if not health_ok:
        health_pass = False
        overall_ok = False

    if not execution_id:
        trigger_pass = False
        overall_ok = False

    if final_status in {"completed", "success"}:
        poll_pass = True
        out = final_payload.get("output_summary") or {}
        if out and out.get("result") is not None:
            result_pass = True
        if not final_payload.get("completed_at"):
            result_pass = False
            print("completed_at missing in execution response; ensure migrations ran and backend returns completed_at")
            overall_ok = False
    else:
        # Provide clearer failure messages for common terminal states
        if final_status == "failed_to_trigger":
            print("Execution failed to trigger. Backend could not reach n8n.")
            print("Execution record:", final_payload)
            print("Error detail:", (final_payload or {}).get("output_summary"))
            overall_ok = False
        elif final_status == "failed":
            print("Workflow executed but returned failure. Check n8n workflow logs.")
            print("Execution record:", final_payload)
            overall_ok = False
        elif final_status == "timeout":
            print("Workflow was triggered but no callback received. Check N8N_CALLBACK_SECRET and BACKEND_PUBLIC_URL.")
            print("Execution record:", final_payload)
            overall_ok = False
        else:
            print("Execution did not complete successfully. status=", final_status, "payload=", final_payload)
            overall_ok = False

    print("========== E2E TEST RESULTS ===========")
    print(f"Health Check:     {'✅ PASS' if health_pass else '❌ FAIL'}")
    print(f"Trigger Workflow: {'✅ PASS' if trigger_pass else '❌ FAIL'} (request_id: {execution_id if execution_id else 'N/A'})")
    print(f"Execution Poll:   {'✅ PASS' if poll_pass else '❌ FAIL'} (status: {final_status})")
    print(f"Result Data:      {'✅ PASS' if result_pass else '❌ FAIL'}")
    print("=======================================")

    if not overall_ok:
        if not os.getenv('N8N_API_KEY'):
            print('\nHint: N8N_API_KEY may be missing or incorrect.')
        print('Suggested fixes: verify Railway env vars, run DB migrations with scripts/run_migrations.py, and ensure n8n callback secret is set in the workflow.')
        raise AssertionError('E2E checks failed')

    print('\nOVERALL: PASS ✅')
