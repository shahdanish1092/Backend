#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

import httpx

file_path = root / "hr_executor_import_final_v2.json"
if not file_path.exists():
    print("Workflow file not found:", file_path)
    raise SystemExit(1)

with open(file_path, "r", encoding="utf-8") as f:
    payload = json.load(f)

# payload may be a list of workflows
workflows = payload if isinstance(payload, list) else [payload]

n8n_base = os.environ.get("N8N_BASE_URL")
if not n8n_base:
    raise RuntimeError("N8N_BASE_URL must be set")

headers = {}
api_key = os.environ.get("N8N_API_KEY")
if api_key:
    headers["X-N8N-API-KEY"] = api_key

created = []
with httpx.Client(timeout=30.0) as client:
    for wf in workflows:
        # build minimal payload expected by n8n create API
        payload = {
            "name": wf.get("name") or "Imported workflow",
            "nodes": wf.get("nodes", []),
            "connections": wf.get("connections", {}),
            # use an empty settings object to avoid sending fields rejected by the n8n API
            "settings": {},
        }
        if wf.get("description"):
            payload["description"] = wf.get("description")

        url = f"{n8n_base.rstrip('/')}/api/v1/workflows"
        resp = client.post(url, json=payload, headers=headers)
        try:
            resp.raise_for_status()
        except Exception as exc:
            print("Failed to import workflow:", exc, resp.text)
            raise
        created_wf = resp.json()
        created.append(created_wf)

        # n8n treats activation separately; attempt to activate the workflow if an id is returned
        wf_id = created_wf.get("id") or created_wf.get("workflow", {}).get("id")
        if wf_id:
            activate_url = f"{n8n_base.rstrip('/')}/api/v1/workflows/{wf_id}/activate"
            try:
                aresp = client.post(activate_url, headers=headers, timeout=30.0)
                aresp.raise_for_status()
                print(f"Activated workflow {wf_id}")
            except Exception as aexc:
                # activation may not be supported on this n8n instance or may require additional fields
                print(f"Activation failed for {wf_id}:", getattr(aexc, 'response', getattr(aexc, 'args', aexc)))

print("Imported workflows:")
print(json.dumps(created, indent=2))
