from fastapi.testclient import TestClient
from main import app


def test_list_connectors_empty(monkeypatch):
    # patch DB connection to return no rows
    class DummyConn:
        def cursor(self):
            class Cur:
                def __enter__(self_inner):
                    return self_inner

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

                def execute(self_inner, *args, **kwargs):
                    self_inner._rows = []
                    self_inner._row = None

                def fetchall(self_inner):
                    return []

                def fetchone(self_inner):
                    return self_inner._row

            return Cur()

        def close(self):
            return None

    monkeypatch.setattr("routers.connectors.get_db_connection", lambda: DummyConn())

    client = TestClient(app)
    r = client.get("/api/connectors", params={"user_email": "a@b.com"}, headers={"X-User-Email": "a@b.com"})
    assert r.status_code == 200
    assert "connectors" in r.json()


def test_connect_gmail_returns_redirect(monkeypatch):
    class DummyConn:
        def close(self):
            return None

    monkeypatch.setattr("routers.connectors.get_db_connection", lambda: DummyConn())
    client = TestClient(app)
    r = client.post("/api/connectors/gmail/connect", params={"user_email": "a@b.com"}, headers={"X-User-Email": "a@b.com"})
    assert r.status_code == 200
    assert "redirect" in r.json()
