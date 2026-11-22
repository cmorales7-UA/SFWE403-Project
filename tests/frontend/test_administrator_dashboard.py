"""Administrator dashboard integration tests using an isolated SQLite database."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.clients import database
from frontend.routes import dashboard


def make_application(owner_id, program_id, name, status):
    return {
        "owner_id": owner_id,
        "program_id": program_id,
        "applicant_name": name,
        "full_name": name,
        "degree_name": "Software Engineering",
        "degree_program": "Software Engineering",
        "term": "Fall 2027",
        "status": status,
        "campus": "main",
        "fields": {},
        "review": {},
        "submission_date": "",
        "last_updated": "",
    }


def test_dashboard_reads_persistent_applications_and_updates(monkeypatch, tmp_path):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "dashboard.sqlite3"))
    admin = {"id": 99, "user_type": "administrator"}
    monkeypatch.setattr(dashboard.accounts, "session_user", lambda token: admin)
    app = FastAPI()
    app.include_router(dashboard.router)

    database.save_program({"degree_name": "Software Engineering"})
    pending_id = database.save_application(
        make_application(1, 1, "Avery Bennett", "Submitted")
    )
    database.save_application(
        make_application(2, 1, "Maya Thompson", "In Review")
    )

    client = TestClient(app)
    response = client.get("/administrator")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "Avery Bennett" in response.text
    assert "Maya Thompson" in response.text
    assert "Program: " not in response.text
    assert "Not decided" in response.text
    assert "No applications have been created yet." not in response.text
    assert 'class="summary-value">2</strong>' in response.text
    assert response.text.count('class="summary-value">1</strong>') == 3

    # Modify the same record in SQLite, then request a new page.
    changed = database.get_application(pending_id)
    changed["status"] = "In Review"
    database.save_application(changed, pending_id)

    response = client.get("/administrator")
    assert response.status_code == 200
    assert response.text.count('class="summary-value">2</strong>') == 2
    assert response.text.count('class="summary-value">0</strong>') == 1


def test_dashboard_empty_state_and_role_restriction(monkeypatch, tmp_path):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "empty.sqlite3"))
    identity = {"id": 1, "user_type": "administrator"}
    monkeypatch.setattr(
        dashboard.accounts, "session_user", lambda token: identity
    )
    app = FastAPI()
    app.include_router(dashboard.router)
    client = TestClient(app)

    response = client.get("/administrator")
    assert response.status_code == 200
    assert "No applications have been created yet." in response.text
    assert response.text.count('class="summary-value">0</strong>') == 4

    identity["user_type"] = "applicant"
    response = client.get("/administrator")
    assert response.status_code == 403
