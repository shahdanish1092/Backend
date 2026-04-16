#!/usr/bin/env python3
"""Activate an existing n8n workflow via the n8n REST API.

Uses env vars: N8N_BASE_URL, N8N_API_KEY, N8N_BASIC_AUTH_USER, N8N_BASIC_AUTH_PASSWORD, N8N_WORKFLOW_ID
"""
import os
import base64
import httpx
import sys


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

    workflow_id = os.environ.get("N8N_WORKFLOW_ID", "j20n0apNuBZU5Pcv")

    activate_url = n8n_base.rstrip("/") + f"/api/v1/workflows/{workflow_id}/activate"
    headers = build_headers()
    headers.setdefault("ngrok-skip-browser-warning", "true")

    print("Activating workflow", workflow_id, "at", activate_url)
    with httpx.Client(timeout=30.0) as client:
        r = client.post(activate_url, headers=headers)
        print(r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text)


if __name__ == '__main__':
    main()
