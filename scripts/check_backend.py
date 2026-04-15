#!/usr/bin/env python3
import os
import httpx

url = os.environ.get("BACKEND_PUBLIC_URL", "https://backend-production-8d62.up.railway.app").rstrip('/') + '/health'
print('Checking', url)
try:
    r = httpx.get(url, timeout=15.0)
    print(r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)
except Exception as exc:
    print('ERROR', exc)
