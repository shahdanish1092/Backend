#!/usr/bin/env python3
"""Fetch credentials from an n8n instance and print IDs for Gmail/Sheets/Calendar.

Usage:
  Set `N8N_API_KEY` and optionally `N8N_BASE_URL`, then run:
    python scripts/get_n8n_credentials.py

This script will exit with code 0 if all three credentials are found, otherwise 2.
"""
import os
import sys
import requests


def main():
    base = os.getenv("N8N_BASE_URL", "https://n8n-production-8c140.up.railway.app").rstrip("/")
    api_key = os.getenv("N8N_API_KEY")
    if not api_key:
        print("ERROR: N8N_API_KEY not set in environment", file=sys.stderr)
        sys.exit(1)

    url = f"{base}/api/v1/credentials"
    headers = {"X-N8N-API-KEY": api_key}
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code != 200:
        print(f"ERROR: Failed to fetch credentials: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(2)

    creds = resp.json()
    # creds is expected to be a list
    gmail = None
    sheets = None
    calendar = None

    for c in creds:
        name = (c.get("name") or "").lower()
        cid = c.get("id")
        ctype = c.get("type") or c.get("credentialType") or ""
        print(f"Found credential: id={cid} name={c.get('name')} type={ctype}")
        if "gmail" in name or "gmail" in (ctype or ""):
            gmail = c
        if "sheets" in name or "sheet" in name or "sheets" in (ctype or ""):
            sheets = c
        if "calendar" in name or "calendar" in (ctype or ""):
            calendar = c

    missing = []
    if not gmail:
        missing.append("Gmail OAuth2")
    if not sheets:
        missing.append("Google Sheets OAuth2")
    if not calendar:
        missing.append("Google Calendar OAuth2")

    print("\nSummary:")
    if gmail:
        print(f"- Gmail OAuth2: id={gmail.get('id')} name={gmail.get('name')}")
    if sheets:
        print(f"- Google Sheets OAuth2: id={sheets.get('id')} name={sheets.get('name')}")
    if calendar:
        print(f"- Google Calendar OAuth2: id={calendar.get('id')} name={calendar.get('name')}")

    if missing:
        print('\nMISSING credentials: ' + ', '.join(missing), file=sys.stderr)
        sys.exit(2)

    print('\nAll required credentials found.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
