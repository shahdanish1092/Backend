import os
import importlib.util
from fastapi.testclient import TestClient


def test_run_migrations_unauthorized(monkeypatch):
    # Ensure webhook secret is configured, then call endpoint without header -> 401
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")

    # Load the local fastapi/run_migrations.py module by path to avoid shadowing the installed fastapi package
    migrations_path = os.path.join(os.path.dirname(__file__), "..", "fastapi", "run_migrations.py")
    migrations_path = os.path.abspath(migrations_path)
    spec = importlib.util.spec_from_file_location("local_run_migrations", migrations_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    migrations_app = module.app

    client = TestClient(migrations_app)
    r = client.post("/internal/run_migrations")
    assert r.status_code == 401
