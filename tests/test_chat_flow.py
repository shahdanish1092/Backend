from fastapi.testclient import TestClient
from main import app
import routers.chat as chat_module
import routers.internal as internal_module


def test_classify_invoice():
    out = chat_module._classify_text_simple("Please process this invoice from Acme Corp for $1234")
    assert out["domain"] == "invoices"


def test_n8n_callback_rejects_invalid_secret():
    client = TestClient(app)
    r = client.post("/api/webhooks/n8n/callback/doesntmatter", json={"status": "success", "data": {}}, headers={"X-N8N-Callback-Secret": "wrong"})
    assert r.status_code == 401


def test_n8n_callback_calls_update(monkeypatch):
    calls = {}

    def fake_update(conn, execution_id, status, result=None, error=None):
        calls['called'] = True

    # Patch the imported update function in internal_module
    monkeypatch.setattr(internal_module, "update_execution_status", fake_update)
    # set proper secret
    monkeypatch.setenv("N8N_CALLBACK_SECRET", "s3cret")
    # ensure execution exists (avoid DB cursor requirement in DummyConn)
    monkeypatch.setattr(internal_module, "get_execution_log", lambda conn, rid: True)
    # patch db connection to dummy
    class DummyConn:
        def close(self):
            return None

    monkeypatch.setattr(internal_module, "get_db_connection", lambda: DummyConn())

    client = TestClient(app)
    r = client.post(
        "/api/webhooks/n8n/callback/test-id",
        json={"status": "success", "data": {"foo": "bar"}},
        headers={"X-N8N-Callback-Secret": "s3cret"},
    )
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
    assert calls.get('called') is True


def test_get_execution_404(monkeypatch):
    # monkeypatch get_execution_log to return None
    def fake_get(conn, request_id):
        return None

    class DummyConn:
        def close(self):
            return None

    monkeypatch.setattr(chat_module, "get_db_connection", lambda: DummyConn())
    monkeypatch.setattr(chat_module, "get_execution_log", lambda conn, rid: None)

    client = TestClient(app)
    r = client.get("/api/executions/nonexistent", headers={"X-User-Email": "a@b.com"})
    assert r.status_code == 404


def test_get_execution_forbidden(monkeypatch):
    sample = {"id": "1", "user_email": "owner@example.com", "module": "hr", "status": "completed"}
    class DummyConn:
        def close(self):
            return None

    monkeypatch.setattr(chat_module, "get_db_connection", lambda: DummyConn())
    monkeypatch.setattr(chat_module, "get_execution_log", lambda conn, rid: sample)

    client = TestClient(app)
    r = client.get("/api/executions/1", headers={"X-User-Email": "other@example.com"})
    assert r.status_code == 403
