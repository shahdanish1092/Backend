#!/usr/bin/env python3
"""Trigger a chat message on the deployed backend and poll the execution status.

Usage:
  Set BACKEND_PUBLIC_URL in env or rely on the default used in this project.
  Then run: `python scripts/e2e_trigger_and_poll.py`
"""
import os
import time
import json
import sys

import httpx


def main():
    backend = os.environ.get("BACKEND_PUBLIC_URL", "https://backend-production-8d62.up.railway.app")
    post_url = backend.rstrip("/") + "/api/chat/message"

    payload = {
        "text": "Please shortlist this candidate's resume and schedule interviews",
        "active_connectors": [],
        "user_email": "e2e-tester@example.com",
    }

    print("Posting chat message to:", post_url)
    with httpx.Client(timeout=30.0) as client:
        try:
            r = client.post(post_url, json=payload)
        except Exception as exc:
            print("POST failed:", exc)
            raise

        try:
            r.raise_for_status()
        except Exception:
            print("POST returned non-2xx:", r.status_code, r.text)
            sys.exit(1)

        data = r.json()
        print(json.dumps(data, indent=2))

        exec_id = data.get("execution_id")
        if not exec_id:
            print("No execution_id returned; aborting")
            return

        # poll execution status
        get_url = backend.rstrip("/") + f"/api/executions/{exec_id}"
        headers = {"X-User-Email": payload["user_email"]}

        print("Polling execution:", exec_id)
        for attempt in range(40):
            try:
                g = client.get(get_url, headers=headers, timeout=15.0)
            except Exception as exc:
                print("GET failed:", exc)
                time.sleep(2)
                continue

            if g.status_code == 200:
                row = g.json()
                status = row.get("status")
                print(f"[{attempt}] status={status}")
                if status and status.lower() in ("completed", "failed", "failed_to_trigger"):
                    print("Final execution:")
                    print(json.dumps(row, indent=2, default=str))
                    return
            else:
                print(f"[{attempt}] GET returned {g.status_code}: {g.text}")

            time.sleep(2)

        print("Polling timed out")


if __name__ == '__main__':
    main()
