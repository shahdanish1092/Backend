#!/usr/bin/env python3
"""Simulate an n8n execution callback by POSTing to the deployed backend's execution callback endpoint.

Defaults to the last execution id we triggered; adjust via REQUEST_ID env if needed.
"""
import os
import json
import sys
import httpx


def main():
    backend = os.environ.get("BACKEND_PUBLIC_URL", "https://backend-production-8d62.up.railway.app").rstrip('/')
    url = backend + "/api/execution-callback"
    request_id = os.environ.get("REQUEST_ID", "291d362d-4da6-4f4a-91c6-5eadea938bae")

    payload = {
        "request_id": request_id,
        "workflow_type": "hr_recruitment",
        "status": "completed",
        "results": [
            {
                "candidate_name": "Test Candidate",
                "candidate_email": "candidate+test@example.com",
                "score": 87,
                "metadata": {"source": "simulated-callback"},
            }
        ],
        "metadata": {"user_email": "e2e-n8n@example.com", "source": "n8n-sim"},
    }

    print("POSTing simulated callback to:", url)
    print(json.dumps(payload, indent=2))

    try:
        r = httpx.post(url, json=payload, timeout=30.0)
    except Exception as exc:
        print("Request failed:", exc)
        sys.exit(1)

    print("Response:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)


if __name__ == '__main__':
    main()
