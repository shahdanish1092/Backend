from fastapi.testclient import TestClient
from main import app
import routers.chat as chat_module
import routers.executions as executions_module
import routers.internal as internal_module


def test_classify_invoice():
    out = chat_module._classify_text_simple("Please process this invoice from Acme Corp for $1234")
    assert out["domain"] == "invoice"


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
    class DummyConn:
        def cursor(self):
            class Cur:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

                def execute(self_inner, *args, **kwargs):
                    self_inner._row = None

                def fetchone(self_inner):
                    return self_inner._row

            return Cur()

        def close(self):
            return None

    monkeypatch.setattr(executions_module, "get_db_connection", lambda: DummyConn())

    client = TestClient(app)
    r = client.get("/api/executions/nonexistent", headers={"X-User-Email": "a@b.com"})
    assert r.status_code == 404


def test_get_execution_forbidden(monkeypatch):
    class DummyConn:
        def cursor(self):
            class Cur:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

                def execute(self_inner, *args, **kwargs):
                    self_inner._row = (
                        "1",
                        "completed",
                        "hr",
                        None,
                        None,
                        None,
                        None,
                        "owner@example.com",
                    )

                def fetchone(self_inner):
                    return self_inner._row

            return Cur()

        def close(self):
            return None

    monkeypatch.setattr(executions_module, "get_db_connection", lambda: DummyConn())

    client = TestClient(app)
    r = client.get("/api/executions/1", headers={"X-User-Email": "other@example.com"})
    assert r.status_code == 403
