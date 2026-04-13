from fastapi.testclient import TestClient

from main import app
from routers import hr_execute


class DummyConnection:
    def close(self):
        return None


def test_rank_candidates_returns_array_when_groq_fails(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(hr_execute, "_attempt_groq_rank", lambda extracted_text, criteria: None)
    monkeypatch.setattr(hr_execute, "get_db_connection", lambda: DummyConnection())
    monkeypatch.setattr(hr_execute, "_merge_step_output", lambda *args, **kwargs: 1)

    response = client.post(
        "/api/rank/candidates",
        json={
            "request_id": "00000000-0000-0000-0000-000000000111",
            "workflow_type": "hr_recruitment",
            "extracted_text": "John Doe john@example.com 5 years Python",
            "criteria": "Python",
            "ranking_logic": "weighted_scoring",
            "candidates": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["ranked_candidates"], list)
    assert body["ranked_candidates"]
    assert body["step_id"] == "rank_candidates"


def test_shortlist_candidates_returns_empty_array(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(hr_execute, "get_db_connection", lambda: DummyConnection())
    monkeypatch.setattr(hr_execute, "_merge_step_output", lambda *args, **kwargs: 1)

    response = client.post(
        "/api/shortlist/candidates",
        json={
            "request_id": "00000000-0000-0000-0000-000000000222",
            "ranked_candidates": [],
            "top_k": 1,
            "timezone": "UTC",
            "working_hours_start": "09:00",
            "working_hours_end": "17:00",
            "slot_duration_minutes": 30,
            "slot_gap_minutes": 15,
            "use_calendar_freebusy": False,
            "freebusy_lookahead_days": 14,
            "calendar_account": "primary",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["shortlisted"] == []
    assert body["step_id"] == "shortlist"


def test_send_email_acknowledges(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(hr_execute, "_reuse_or_create_request", lambda *args, **kwargs: "00000000-0000-0000-0000-000000000333")

    response = client.post(
        "/api/send-email",
        json={
            "request_id": "00000000-0000-0000-0000-000000000333",
            "candidate_email": "candidate@example.com",
            "candidate_name": "Candidate",
            "subject": "Interview",
            "body": "Hello",
            "step_id": "send_emails",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "step_id": "send_emails",
        "request_id": "00000000-0000-0000-0000-000000000333",
    }


def test_create_calendar_event_acknowledges(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(hr_execute, "_reuse_or_create_request", lambda *args, **kwargs: "00000000-0000-0000-0000-000000000444")

    response = client.post(
        "/api/create-calendar-event",
        json={
            "request_id": "00000000-0000-0000-0000-000000000444",
            "candidate_name": "Candidate",
            "candidate_email": "candidate@example.com",
            "start_time": "2026-04-12T10:00:00Z",
            "end_time": "2026-04-12T10:30:00Z",
            "step_id": "schedule_interviews",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "step_id": "schedule_interviews",
        "event_id": "evt_00000000",
        "start_time": "2026-04-12T10:00:00Z",
        "end_time": "2026-04-12T10:30:00Z",
        "request_id": "00000000-0000-0000-0000-000000000444",
    }
