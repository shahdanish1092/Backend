import asyncio

import orchestration


class DummyResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._payload


class DummyAsyncClient:
    def __init__(self, responses, seen_headers):
        self._responses = list(responses)
        self._seen_headers = seen_headers

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        self._seen_headers.append(headers or {})
        return self._responses.pop(0)


def test_get_n8n_executions_falls_back_to_bearer(monkeypatch):
    seen_headers = []
    responses = [
        DummyResponse(401, {"message": "unauthorized"}),
        DummyResponse(200, {"data": [{"id": 1, "request_id": "abc-123"}]}),
    ]

    monkeypatch.setenv("N8N_BASE_URL", "http://localhost:5678")
    monkeypatch.setenv("N8N_API_KEY", "test-token")
    monkeypatch.setattr(
        orchestration.httpx,
        "AsyncClient",
        lambda timeout=20.0: DummyAsyncClient(responses, seen_headers),
    )

    result = asyncio.run(orchestration.get_n8n_executions_for_request("abc-123"))

    assert result["count"] == 1
    assert result["auth_mode"] == "bearer"
    assert seen_headers[0] == {"X-N8N-API-KEY": "test-token"}
    assert seen_headers[1] == {"Authorization": "Bearer test-token"}


def test_ping_n8n_health(monkeypatch):
    seen_headers = []
    responses = [DummyResponse(200, {"status": "ok"})]

    monkeypatch.setenv("N8N_BASE_URL", "http://localhost:5678")
    monkeypatch.setattr(
        orchestration.httpx,
        "AsyncClient",
        lambda timeout=10.0: DummyAsyncClient(responses, seen_headers),
    )

    result = asyncio.run(orchestration.ping_n8n_health())

    assert result == {
        "base_url": "http://localhost:5678",
        "status_code": 200,
        "body": {"status": "ok"},
    }
