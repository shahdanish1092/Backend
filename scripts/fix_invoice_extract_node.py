#!/usr/bin/env python3
"""Replace Extract Invoice Text with Code node; update Groq + callback; PUT + activate."""
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
    if load_dotenv:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def api(method: str, url: str, body: dict | None = None) -> dict:
    key = os.environ.get("N8N_API_KEY", "")
    if not key:
        sys.exit("N8N_API_KEY missing")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"X-N8N-API-KEY": key, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode("utf-8", errors="replace")) from e


EXTRACT_JS = r"""const root = $input.first().json;
const payload = root.body || root;
const fileBase64 = payload.file_base64 || payload.payload?.file_base64 || "";
const filename = payload.filename || payload.payload?.filename || "invoice.pdf";
const userEmail = payload.user_email || payload.payload?.user_email || "";
const requestId = payload.request_id || "";
const callbackUrl = payload.callback_url || "";
const backendBase = payload.backend_base_url ||
                    "https://backend-production-0577.up.railway.app";

return [{
  json: {
    request_id: requestId,
    callback_url: callbackUrl,
    backend_base_url: backendBase,
    user_email: userEmail,
    filename: filename,
    file_base64: fileBase64,
    extracted: true
  }
}];"""


GROQ_JSON_BODY = r"""={
  "model": "llama3-8b-8192",
  "response_format": { "type": "json_object" },
  "max_tokens": 1000,
  "temperature": 0.1,
  "messages": [
    {
      "role": "system",
      "content": "You are an invoice data extraction assistant. Extract structured data from the invoice description provided. Return ONLY valid JSON with these fields: vendor_name, invoice_number, total_amount, invoice_date, line_items (array of objects), confidence_score (0-1), is_invoice (boolean)"
    },
    {
      "role": "user",
      "content": "Extract invoice data from this file: {{ $('Extract Invoice Text').first().json.filename }}\nFile is base64 encoded PDF. User: {{ $('Extract Invoice Text').first().json.user_email }}"
    }
  ]
}"""


def workflow_put_payload(wf: dict) -> dict:
    return {k: wf[k] for k in ("name", "nodes", "connections", "settings", "staticData") if k in wf}


def main() -> int:
    load_env()
    base = (os.environ.get("N8N_BASE_URL") or "https://n8n-production-8c140.up.railway.app").rstrip("/")
    wid = "7GVaSgIqOVLT0vs5"
    v1 = f"{base}/api/v1"

    wf = api("GET", f"{v1}/workflows/{wid}")

    for n in wf["nodes"]:
        if n.get("name") == "Extract Invoice Text":
            n["type"] = "n8n-nodes-base.code"
            n["typeVersion"] = 2
            n["parameters"] = {"jsCode": EXTRACT_JS}
            break
    else:
        print("Extract Invoice Text node not found", file=sys.stderr)
        return 1

    for n in wf["nodes"]:
        if n.get("name") == "Analyze with Groq":
            # typeVersion 1 maps params incorrectly and defaults to GET — use v4.2
            n["typeVersion"] = 4.2
            n["parameters"] = {
                "method": "POST",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "authentication": "none",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {
                            "name": "Authorization",
                            # If GROQ_API_KEY is set when running this script, embed it (avoids $env blocks).
                            # Otherwise use n8n env (set N8N_BLOCK_ENV_ACCESS_IN_NODE=false if denied).
                            "value": (
                                f"Bearer {os.environ['GROQ_API_KEY'].strip()}"
                                if os.environ.get("GROQ_API_KEY", "").strip()
                                else "=Bearer {{ $env.GROQ_API_KEY }}"
                            ),
                        },
                        {"name": "Content-Type", "value": "application/json"},
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": GROQ_JSON_BODY,
                "options": {},
            }
            break

    callback_expr = r"""={{ JSON.stringify({
  execution_id: $('Parse Groq Response').first().json.request_id,
  request_id: $('Parse Groq Response').first().json.request_id,
  status: 'completed',
  result: {
    vendor_name: $('Parse Groq Response').first().json.vendor_name,
    invoice_number: $('Parse Groq Response').first().json.invoice_number,
    total_amount: $('Parse Groq Response').first().json.total_amount,
    invoice_date: $('Parse Groq Response').first().json.invoice_date,
    confidence_score: $('Parse Groq Response').first().json.confidence_score
  }
}) }}"""

    for n in wf["nodes"]:
        if n.get("name") == "Send Execution Callback":
            n["typeVersion"] = 4.2
            n["parameters"] = {
                "method": "POST",
                "url": "={{ $('Extract Context').first().json.callback_url }}",
                "authentication": "none",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "X-N8N-Callback-Secret", "value": "={{ $('Extract Context').first().json.n8n_callback_secret }}"},
                        {"name": "Content-Type", "value": "application/json"},
                    ]
                },
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": callback_expr,
                "options": {},
            }
            break

    api("PUT", f"{v1}/workflows/{wid}", workflow_put_payload(wf))
    print("PUT ok")
    api("POST", f"{v1}/workflows/{wid}/activate", {})
    print("Activated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
