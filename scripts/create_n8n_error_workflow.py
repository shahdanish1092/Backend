#!/usr/bin/env python3
"""Create Global Error Handler workflow and attach to Invoice + HR workflows."""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def load_env() -> None:
    root = Path(__file__).resolve().parents[1]
    if load_dotenv:
        load_dotenv(root / ".env")


def api(method: str, url: str, body: dict | None = None) -> dict:
    key = os.environ.get("N8N_API_KEY", "")
    if not key:
        print("N8N_API_KEY missing", file=sys.stderr)
        sys.exit(1)
    data = None
    headers = {"X-N8N-API-KEY": key, "Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err}") from e


def workflow_put_payload(wf: dict) -> dict:
    """Fields accepted by PUT /workflows/{id} (n8n v1)."""
    keys = ("name", "nodes", "connections", "settings", "staticData")
    return {k: wf[k] for k in keys if k in wf}


# Extract callback_url + request_id from any node output in the failed execution snapshot
CODE_EXTRACT = r"""const e = $input.first().json.execution;
const errMsg = e?.error?.message || 'workflow error';
let callback_url = e?.customData?.callback_url || '';
let request_id = e?.customData?.request_id || '';
const rd = e?.data?.resultData?.runData;
if (rd && typeof rd === 'object') {
  for (const runs of Object.values(rd)) {
    const runArr = Array.isArray(runs) ? runs : [];
    for (const run of runArr) {
      const items = run?.data?.main?.[0];
      if (!Array.isArray(items)) continue;
      for (const item of items) {
        const j = item?.json;
        if (!j || typeof j !== 'object') continue;
        if (!callback_url && j.callback_url) callback_url = String(j.callback_url);
        if (!request_id && (j.request_id || j.body?.request_id)) {
          request_id = String(j.request_id || j.body?.request_id);
        }
        if (callback_url && request_id) break;
      }
      if (callback_url && request_id) break;
    }
    if (callback_url && request_id) break;
  }
}
return [{ json: { callback_url, request_id, error: errMsg } }];"""


def main() -> int:
    load_env()
    base = (os.environ.get("N8N_BASE_URL") or "https://n8n-production-8c140.up.railway.app").rstrip("/")
    v1 = f"{base}/api/v1"

    new_wf = {
        "name": "Global Error Handler",
        "nodes": [
            {
                "id": "err-trigger-1",
                "name": "Error Trigger",
                "type": "n8n-nodes-base.errorTrigger",
                "typeVersion": 1,
                "position": [200, 200],
                "parameters": {},
            },
            {
                "id": "extract-callback-1",
                "name": "Extract Callback Context",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [380, 200],
                "parameters": {"jsCode": CODE_EXTRACT},
            },
            {
                "id": "post-fail-1",
                "name": "Post Failure Callback",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [600, 200],
                "parameters": {
                    "method": "POST",
                    "url": "={{ $json.callback_url }}",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": (
                        "={{ JSON.stringify({ "
                        "request_id: $json.request_id, "
                        "execution_id: $json.request_id, "
                        "status: 'failed', "
                        "error: $json.error "
                        "}) }}"
                    ),
                    "options": {"timeout": 30000},
                },
            },
        ],
        "connections": {
            "Error Trigger": {"main": [[{"node": "Extract Callback Context", "type": "main", "index": 0}]]},
            "Extract Callback Context": {"main": [[{"node": "Post Failure Callback", "type": "main", "index": 0}]]},
        },
        "settings": {"executionOrder": "v1"},
    }

    existing = os.environ.get("N8N_ERROR_WORKFLOW_ID", "").strip()
    if existing:
        err_id = existing
        print("Using existing error workflow id:", err_id)
    else:
        print("Creating Global Error Handler...")
        created = api("POST", f"{v1}/workflows", new_wf)
        err_id = created.get("id") or created.get("data", {}).get("id")
        if not err_id:
            print("Unexpected response:", json.dumps(created)[:800], file=sys.stderr)
            return 1
        print("Created error workflow id:", err_id)
        print("Activating error workflow...")
        api("POST", f"{v1}/workflows/{err_id}/activate", {})

    for wid, label in (
        ("7GVaSgIqOVLT0vs5", "Invoice Processor"),
        ("V1v6fXo7jskZjvif", "HR Recruitment Executor"),
    ):
        print(f"PUT settings.errorWorkflow on {label} ({wid})...")
        wf = api("GET", f"{v1}/workflows/{wid}")
        settings = dict(wf.get("settings") or {})
        settings["errorWorkflow"] = err_id
        wf["settings"] = settings
        api("PUT", f"{v1}/workflows/{wid}", workflow_put_payload(wf))

    for wid in ("7GVaSgIqOVLT0vs5", "V1v6fXo7jskZjvif"):
        wf = api("GET", f"{v1}/workflows/{wid}")
        ew = (wf.get("settings") or {}).get("errorWorkflow")
        print(f"Verify {wid} errorWorkflow = {ew} (expected {err_id})")
        if str(ew) != str(err_id):
            print("MISMATCH", file=sys.stderr)
            return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
