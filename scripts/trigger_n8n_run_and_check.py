#!/usr/bin/env python3
"""Trigger an n8n workflow run and check n8n executions for the generated execution_id.

This will not modify the project's DB; it triggers the workflow and inspects n8n's execution records.
"""
import os
import time
import uuid
import json
import base64
import httpx


def build_headers():
    headers = {}
    api_key = os.environ.get("N8N_API_KEY")
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    return headers


def main():
    n8n_base = os.environ.get("N8N_BASE_URL") or os.environ.get("N8N_WEBHOOK_BASE_URL") or "http://127.0.0.1:5678"
    workflow_id = os.environ.get("N8N_WORKFLOW_ID") or "cUNV8MuHEZMQpn4U"
    backend_cb = (os.environ.get("BACKEND_PUBLIC_URL") or os.environ.get("FASTAPI_BASE_URL") or "http://127.0.0.1:8000").rstrip('/') + "/api/execution-callback"

    exec_id = str(uuid.uuid4())
    body = {
        "execution_id": exec_id,
        "input": {"text": "Please shortlist candidate resume for Senior Backend Engineer", "connectors": [], "user_email": "e2e-n8n@example.com"},
        "callback_url": backend_cb,
    }

    # first try the /api/v1/workflows/{id}/run endpoint
    run_url = n8n_base.rstrip('/') + f"/api/v1/workflows/{workflow_id}/run"
    headers = build_headers()
    headers.setdefault("ngrok-skip-browser-warning", "true")

    print("Attempting /api/v1/workflows/{id}/run endpoint")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(run_url, json=body, headers=headers)
        if r.status_code == 405:
            print("Run endpoint returned 405; falling back to webhook trigger")
            # fallback: trigger the workflow webhook path (common pattern for workflows with Webhook trigger)
            webhook_path = os.environ.get("N8N_WEBHOOK_PATH", f"execute-workflow-{workflow_id}")
            webhook_url = n8n_base.rstrip('/') + f"/webhook/{webhook_path}"
            print("Triggering webhook at", webhook_url)
            wr = client.post(webhook_url, json=body)
            try:
                wr.raise_for_status()
            except Exception:
                print("Webhook trigger failed:", wr.status_code, wr.text)
                return
            print("Webhook trigger response:", wr.status_code, wr.text[:1000])
        else:
            try:
                r.raise_for_status()
                print("Run response:", r.status_code)
                try:
                    print(json.dumps(r.json(), indent=2))
                except Exception:
                    print(r.text[:1000])
            except Exception:
                print("Run failed:", r.status_code, r.text)
                return

        # poll n8n executions
        rest_url = n8n_base.rstrip('/') + "/rest/executions"
        print("Polling n8n executions for execution_id", exec_id)
        # Try multiple auth header modes if the first attempt is unauthorized
        api_key = os.environ.get("N8N_API_KEY")
        header_modes = []
        if api_key:
            header_modes.append({"X-N8N-API-KEY": api_key})
            header_modes.append({"Authorization": f"Bearer {api_key}"})
        # also try no-auth (some n8n instances expose read endpoints without API key)
        header_modes.append({})

        for i in range(20):
            for mode_idx, h in enumerate(header_modes):
                er = client.get(rest_url, headers=h, timeout=20.0)
                if er.status_code == 401:
                    print(f"Attempt {i} mode {mode_idx}: unauthorized")
                    continue
                if er.status_code != 200:
                    print(f"Attempt {i} mode {mode_idx}: failed to list executions", er.status_code, er.text[:200])
                    continue
                payload = er.json()
                executions = payload.get("data") if isinstance(payload, dict) and "data" in payload else (payload if isinstance(payload, list) else [])
                matches = [e for e in executions if exec_id in json.dumps(e)]
                print(f"Attempt {i} mode {mode_idx}: found {len(matches)} matches")
                if matches:
                    for m in matches:
                        print(json.dumps(m, indent=2)[:4000])
                    return
            time.sleep(2)

        print("No matching n8n execution found for", exec_id)


if __name__ == '__main__':
    main()
