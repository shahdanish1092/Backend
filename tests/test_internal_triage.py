from fastapi.testclient import TestClient

from main import app
from routers import internal


class DummyConnection:
    def close(self):
        return None


class DummyResponse:
    status_code = 200
    text = "Workflow was started"


def test_triage_returns_request_id_when_n8n_trigger_fails(monkeypatch):
    client = TestClient(app)
    state = {"created": None, "updates": []}

    def fake_get_db_connection():
        return DummyConnection()

    def fake_create_execution_log(conn, user_email, module, input_payload, status, output_summary=None):
        state["created"] = {
            "user_email": user_email,
            "module": module,
            "input_payload": input_payload,
            "status": status,
        }
        return "00000000-0000-0000-0000-000000000111"

    def fake_update_execution_log(conn, request_id, *, status=None, output_summary=None, input_payload=None):
        state["updates"].append(
            {
                "request_id": request_id,
                "status": status,
                "output_summary": output_summary,
                "input_payload": input_payload,
            }
        )
        return 1

    async def fake_post_with_retry(url, *, json_body, headers=None, timeout=15.0, attempts=3):
        assert state["created"] is not None
        raise RuntimeError("simulated n8n timeout")

    monkeypatch.setenv("N8N_HR_WEBHOOK_URL", "http://127.0.0.1:5678/webhook/execute-workflow")
    monkeypatch.setattr(internal, "get_db_connection", fake_get_db_connection)
    monkeypatch.setattr(internal, "create_execution_log", fake_create_execution_log)
    monkeypatch.setattr(internal, "update_execution_log", fake_update_execution_log)
    monkeypatch.setattr(internal, "post_with_retry", fake_post_with_retry)

    response = client.post(
        "/api/internal/triage",
        json={
            "user_email": "triage-unit@example.com",
            "category": "Recruitment",
            "email_data": {
                "subject": "Test",
                "body": "candidate body",
                "from": "applicant@example.com",
                "attachments": [],
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == "00000000-0000-0000-0000-000000000111"
    assert response.json()["status"] == "failed_to_trigger"
    assert state["created"]["status"] == "created"
    assert any(update["status"] == "failed_to_trigger" for update in state["updates"])


def test_triage_marks_running_when_n8n_trigger_succeeds(monkeypatch):
    client = TestClient(app)
    state = {"updates": []}

    def fake_get_db_connection():
        return DummyConnection()

    def fake_create_execution_log(conn, user_email, module, input_payload, status, output_summary=None):
        return "00000000-0000-0000-0000-000000000222"

    def fake_update_execution_log(conn, request_id, *, status=None, output_summary=None, input_payload=None):
        state["updates"].append(status)
        return 1

    async def fake_post_with_retry(url, *, json_body, headers=None, timeout=15.0, attempts=3):
        return DummyResponse()

    monkeypatch.setenv("N8N_HR_WEBHOOK_URL", "http://127.0.0.1:5678/webhook/execute-workflow")
    monkeypatch.setattr(internal, "get_db_connection", fake_get_db_connection)
    monkeypatch.setattr(internal, "create_execution_log", fake_create_execution_log)
    monkeypatch.setattr(internal, "update_execution_log", fake_update_execution_log)
    monkeypatch.setattr(internal, "post_with_retry", fake_post_with_retry)

    response = client.post(
        "/api/internal/triage",
        json={
            "user_email": "triage-unit@example.com",
            "category": "Recruitment",
            "email_data": {
                "subject": "Test",
                "body": "candidate body",
                "from": "applicant@example.com",
                "attachments": [],
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "request_id": "00000000-0000-0000-0000-000000000222",
        "status": "triggered",
        "workflow": "hr_recruitment",
    }
    assert "triggering" in state["updates"]
    assert "running" in state["updates"]
