#!/usr/bin/env python3
"""Patch live n8n Invoice + HR workflows (Groq model, Extract Context fallbacks).

Requires: N8N_BASE_URL, N8N_API_KEY
"""
import json
import os
import sys
import urllib.error
import urllib.request


def api_request(method: str, url: str, body: dict | None = None) -> dict:
    key = os.environ.get("N8N_API_KEY", "")
    data = None
    headers = {"X-N8N-API-KEY": key, "Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {url}: {err}") from e


def patch_invoice(wf: dict) -> bool:
    changed = False
    for n in wf.get("nodes", []):
        if n.get("name") == "Analyze with Groq":
            jb = n.get("parameters", {}).get("jsonBody") or ""
            if "llama-3.3-70b-versatile" in jb:
                n["parameters"]["jsonBody"] = jb.replace(
                    "llama-3.3-70b-versatile", "llama3-8b-8192"
                )
                changed = True
            elif "llama3-8b-8192" not in jb and "llama3-8b-8192" not in str(n.get("parameters", {})):
                # idempotent re-run
                pass
    return changed


def patch_validate_secret(wf: dict) -> bool:
    changed = False
    for n in wf.get("nodes", []):
        if n.get("name") != "Validate Backend Secret":
            continue
        conds = n.get("parameters", {}).get("conditions", {}).get("string") or []
        for c in conds:
            if c.get("value2") == "={{ $json.body.n8n_callback_secret || '' }}":
                c["value2"] = "={{ $json.body?.n8n_callback_secret || $json.n8n_callback_secret || '' }}"
                changed = True
    return changed


def patch_hr_extract(wf: dict) -> bool:
    changed = False
    for n in wf.get("nodes", []):
        if n.get("name") != "Extract Context":
            continue
        vals = n.get("parameters", {}).get("values", {}).get("string") or []
        repl = {
            "request_id": "={{ $json.body?.request_id || $json.request_id }}",
            "workflow_type": "={{ $json.body?.workflow_type || $json.workflow_type || 'hr' }}",
            "user_email": "={{ $json.body?.payload?.user_email || $json.body?.user_email || $json.payload?.user_email || $json.user_email || '' }}",
            "callback_url": "={{ $json.body?.callback_url || $json.callback_url }}",
            "backend_base_url": "={{ $json.body?.backend_base_url || $json.backend_base_url || 'http://127.0.0.1:8000' }}",
            "n8n_callback_secret": "={{ $json.body?.n8n_callback_secret || $json.n8n_callback_secret || '' }}",
            "criteria": "={{ $json.body?.payload?.criteria || $json.payload?.criteria || '' }}",
            "top_k": "={{ $json.body?.payload?.top_k || $json.payload?.top_k || 1 }}",
            "extracted_text": "={{ $json.body?.payload?.extracted_text || $json.payload?.extracted_text || $json.body?.payload?.email_data?.body || $json.payload?.email_data?.body || $json.body?.payload?.email_data?.subject || '' }}",
        }
        for row in vals:
            name = row.get("name")
            if name in repl:
                if row.get("value") != repl[name]:
                    row["value"] = repl[name]
                    changed = True
    return changed


def _workflow_put_payload(wf: dict) -> dict:
    """Send only fields accepted by PUT /api/v1/workflows/{id}."""
    keys = ("name", "nodes", "connections", "settings", "staticData")
    return {k: wf[k] for k in keys if k in wf}


def main() -> int:
    base = (os.environ.get("N8N_BASE_URL") or "").rstrip("/")
    if not base or not os.environ.get("N8N_API_KEY"):
        print("Set N8N_BASE_URL and N8N_API_KEY", file=sys.stderr)
        return 1

    inv_id = os.environ.get("N8N_INVOICE_WORKFLOW_ID", "7GVaSgIqOVLT0vs5")
    hr_id = os.environ.get("N8N_HR_WORKFLOW_ID", "V1v6fXo7jskZjvif")

    def patch_both(wf: dict, wid: str) -> bool:
        name = (wf.get("name") or "").lower()
        a = patch_invoice(wf) if "invoice" in name else False
        b = patch_validate_secret(wf)
        c = patch_hr_extract(wf) if wid == hr_id else False
        return a or b or c

    for label, wid in (("invoice", inv_id), ("hr", hr_id)):
        url = f"{base}/api/v1/workflows/{wid}"
        wf = api_request("GET", url)
        if patch_both(wf, wid):
            api_request("PUT", url, _workflow_put_payload(wf))
            print(f"Patched {label} workflow {wid}")
        else:
            print(f"No changes needed for {label} workflow {wid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
