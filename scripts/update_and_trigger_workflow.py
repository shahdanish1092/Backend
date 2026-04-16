#!/usr/bin/env python3
"""Update an imported n8n workflow's webhook path, activate it, and trigger it with a test payload.

Env:
  N8N_BASE_URL, N8N_API_KEY, N8N_BASIC_AUTH_USER, N8N_BASIC_AUTH_PASSWORD
  N8N_WORKFLOW_ID (optional)
  BACKEND_PUBLIC_URL (for callback)
"""
import os
import sys
import uuid
import time
import base64
import json
import httpx


def build_headers():
    headers = {}
    api_key = os.environ.get("N8N_API_KEY")
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    return headers


def main():
    n8n_base = os.environ.get("N8N_BASE_URL")
    if not n8n_base:
        print("N8N_BASE_URL must be set", file=sys.stderr)
        sys.exit(1)

    wf_id = os.environ.get("N8N_WORKFLOW_ID", "j20n0apNuBZU5Pcv")
    new_path = f"execute-workflow-{wf_id}"
    headers = build_headers()
    headers.setdefault("ngrok-skip-browser-warning", "true")

    get_url = n8n_base.rstrip('/') + f"/api/v1/workflows/{wf_id}"
    print("Fetching workflow", wf_id)
    with httpx.Client(timeout=30.0) as client:
        r = client.get(get_url, headers=headers)
        try:
            r.raise_for_status()
        except Exception:
            print("Failed to fetch workflow:", r.status_code, r.text)
            sys.exit(1)
        wf = r.json()

        # modify webhook nodes
        nodes = wf.get("nodes") or []
        changed = False
        for node in nodes:
            if node.get("type") == "n8n-nodes-base.webhook":
                params = node.setdefault("parameters", {})
                old = params.get("path")
                if old != new_path:
                    print(f"Changing webhook path '{old}' -> '{new_path}'")
                    params["path"] = new_path
                    changed = True

        if not changed:
            print("No webhook node path changed (already set?)")

        payload = {
            "name": wf.get("name") or f"workflow-{wf_id}",
            "nodes": nodes,
            "connections": wf.get("connections", {}),
            "settings": wf.get("settings", {}),
            "description": wf.get("description") or "",
        }

        put_url = n8n_base.rstrip('/') + f"/api/v1/workflows/{wf_id}"
        print("Updating workflow with new webhook path")
        upr = client.put(put_url, json=payload, headers=headers)
        if upr.status_code >= 400:
            print("Update failed:", upr.status_code, upr.text)
            sys.exit(1)
        print("Update ok")

        # activate
        act_url = n8n_base.rstrip('/') + f"/api/v1/workflows/{wf_id}/activate"
        print("Activating workflow", wf_id)
        ar = client.post(act_url, headers=headers)
        if ar.status_code >= 400:
            print("Activation failed:", ar.status_code, ar.text)
            # don't exit; we might still trigger webhook for testing
        else:
            print("Activated")

        # trigger webhook
        request_id = str(uuid.uuid4())
        backend = os.environ.get("BACKEND_PUBLIC_URL", "https://backend-production-8d62.up.railway.app").rstrip('/')
        callback_url = backend + f"/api/webhooks/n8n/callback/{request_id}"

        webhook_url = n8n_base.rstrip('/') + f"/webhook/{new_path}"
        body = {
            "request_id": request_id,
            "workflow_type": "hr_recruitment",
            "user_email": "e2e-n8n@example.com",
            "payload": {
                "email_data": {"subject": "E2E Test", "body": "Please shortlist this resume.", "from": "applicant@example.com", "attachments": []},
            },
            "callback_url": callback_url,
        }

        print("Triggering webhook at", webhook_url)
        tr = client.post(webhook_url, json=body, headers={})
        print("Webhook trigger status", tr.status_code, tr.text[:200])

        # wait and ask backend for n8n executions (best-effort)
        time.sleep(2)
        try:
            info_url = backend + f"/api/internal/n8n/executions/{request_id}"
            print("Asking backend for n8n executions info at", info_url)
            br = client.get(info_url, timeout=30.0)
            print("Backend info status", br.status_code)
            try:
                print(json.dumps(br.json(), indent=2))
            except Exception:
                print(br.text[:1000])
        except Exception as exc:
            print("Failed to query backend for executions:", exc)


if __name__ == '__main__':
    main()
