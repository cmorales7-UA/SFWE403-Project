"""Database integration tests for Advisor, Reviewer, Reference, and IT dashboards."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.clients import database, reviewer_data
from frontend.routes import dashboard


@pytest.fixture
def browser(tmp_path, monkeypatch):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "role-dashboards.sqlite3"))
    current = {
        "id": 1, "user_type": "advisor",
        "email": "advisor@example.test",
        "assigned_program_ids": [],
    }
    monkeypatch.setattr(
        dashboard.accounts, "session_user", lambda token: current
    )
    app = FastAPI()
    app.include_router(dashboard.router)
    return TestClient(app), current


def add_user(name, role, email=None):
    return database.save_user({
        "username": name,
        "email": email or f"{name}@example.test",
        "first_name": name.title(),
        "last_name": "Example",
        "user_type": role,
        "assigned_program_ids": [],
    })


def add_app(name, program_id, status, review=None):
    return database.save_application({
        "owner_id": 100,
        "program_id": program_id,
        "applicant_name": name,
        "full_name": name,
        "degree_name": "Software Engineering",
        "degree_program": "Software Engineering",
        "status": status,
        "term": "Fall 2027",
        "campus": "main",
        "fields": {},
        "review": review or {},
    })


def test_advisor_dashboard_shows_only_assigned_program_applications(browser):
    client, identity = browser
    se = database.save_program({"degree_name": "Software Engineering"})
    cs = database.save_program({"degree_name": "Computer Science"})
    identity["assigned_program_ids"] = [se]

    pending_id = add_app("Avery Bennett", se, "Submitted")
    add_app(
        "Maya Thompson", se, "In Review",
        {"reviewed_at": "2026-11-20T12:00:00+00:00"},
    )
    add_app("Outside Program", cs, "Submitted")

    response = client.get("/advisor")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "Avery Bennett" in response.text
    assert "Maya Thompson" in response.text
    assert "Outside Program" not in response.text
    assert 'class="summary-value">2</strong>' in response.text
    assert response.text.count('class="summary-value">1</strong>') == 3

    updated = database.get_application(pending_id)
    updated["review"] = {"reviewed_at": "2026-11-21T12:00:00+00:00"}
    updated["status"] = "In Review"
    database.save_application(updated, pending_id)
    refreshed = client.get("/advisor")
    assert refreshed.text.count('class="summary-value">2</strong>') == 2
    assert 'class="summary-value">0</strong>' in refreshed.text


def test_reviewer_dashboard_tracks_saved_recommendations(browser):
    client, identity = browser
    program = database.save_program({"degree_name": "Software Engineering"})
    other_program = database.save_program({"degree_name": "Computer Science"})
    reviewer_id = add_user("reviewer", "reviewer")
    identity.update({
        "id": reviewer_id,
        "user_type": "reviewer",
        "assigned_program_ids": [program],
    })

    first = add_app("Avery Bennett", program, "In Review")
    second = add_app("Maya Thompson", program, "In Review")
    other = add_app("Other Program", other_program, "In Review")
    for app_id in (first, second, other):
        database.save_review_assignment(app_id, reviewer_id, 99, "2026-12-15")

    before = client.get("/reviewer")
    assert before.status_code == 200
    assert before.headers["cache-control"] == "no-store"
    assert "Avery Bennett" in before.text
    assert "Maya Thompson" in before.text
    assert "Other Program" not in before.text
    assert before.text.count('class="summary-value">2</strong>') == 2
    assert before.text.count('class="summary-value">0</strong>') == 2

    reviewer_data.save_recommendation(first, reviewer_id, "recommend", "Good")
    after = client.get("/reviewer")
    assert 'class="summary-value">1</strong>' in after.text
    assert "Recommend" in after.text
    assert "Not entered" in after.text
    assert "/reviewer/applications?application=" in after.text


def test_reference_dashboard_only_shows_requests_for_own_email(browser):
    client, identity = browser
    program = database.save_program({"degree_name": "Software Engineering"})
    first = add_app("Avery Bennett", program, "Submitted")
    second = add_app("Other Student", program, "Submitted")
    identity.update({
        "id": 60,
        "user_type": "reference",
        "email": "reference@example.test",
    })

    request_args = (60, 1, "Dr Example", "reference@example.test", "ref1", "hashed-code")
    database.save_recommendation_request(first, *request_args)
    database.save_recommendation_request(
        second, 60, 1, "Other",
        "someoneelse@example.test", "ref2", "hashed-code",
    )

    response = client.get("/reference")
    assert response.status_code == 200
    assert "Avery Bennett" in response.text
    assert "Other Student" not in response.text
    assert "Requested" in response.text
    assert response.text.count('class="summary-value">1</strong>') == 3

    identity["email"] = "notamatch@example.test"
    second_view = client.get("/reference")
    assert "Avery Bennett" not in second_view.text
    assert 'class="summary-value">0</strong>' in second_view.text


def test_it_dashboard_uses_registered_accounts_and_not_fictional_auth_states(browser):
    client, identity = browser
    identity.update({"user_type": "it_support", "id": 90})
    add_user("avery", "applicant")
    add_user("reviewer", "reviewer")
    add_user("support", "it_support")

    response = client.get("/it-support")
    assert response.status_code == 200
    assert "avery@example.test" in response.text
    assert "reviewer@example.test" in response.text
    assert "support@example.test" in response.text
    assert "Pending Authorization" not in response.text
    assert "Authorized Accounts" not in response.text
    assert 'class="summary-value">3</strong>' in response.text
    assert 'class="summary-value">1</strong>' in response.text
    assert 'class="summary-value">2</strong>' in response.text


@pytest.mark.parametrize("route,role", [
    ("/advisor", "advisor"),
    ("/reviewer", "reviewer"),
    ("/reference", "reference"),
    ("/it-support", "it_support"),
])
def test_role_dashboard_rejects_other_roles(browser, route, role):
    client, identity = browser
    identity["user_type"] = "applicant"
    assert client.get(route).status_code == 403
