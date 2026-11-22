"""End-to-end page/API integration for user management and reports.

The tests use isolated temporary SQLite files. Nothing modifies the demo DB.
"""
import csv
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.clients import database
from backend.routes.api import router as api_router
from backend.service import accounts, graduate_college
from frontend.routes import administrator, reports


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "admin-pages.sqlite3"))

    admin_id = database.save_user({
        "username": "admin", "email": "admin@example.test",
        "first_name": "Alex", "last_name": "Administrator",
        "phone": "5550001111", "net_id": "admin",
        "user_type": "administrator", "assigned_program_ids": [],
    })
    actor = next(user for user in database.users() if user["id"] == admin_id)
    monkeypatch.setattr(accounts, "session_user", lambda token: actor)

    program_id = database.save_program({
        "degree_name": "Software Engineering", "degree_level": "masters",
        "terms_offered": ["Fall 2027", "Spring 2028"],
        "campus_offered": ["main", "online"],
    })

    app = FastAPI()
    app.include_router(administrator.router)
    app.include_router(reports.router)
    app.include_router(api_router)
    return TestClient(app), actor, program_id


def create_account(username, role="applicant", **changes):
    record = {
        "username": username,
        "email": f"{username}@example.test",
        "first_name": username.title(),
        "last_name": "Test",
        "phone": "5550001111",
        "net_id": username,
        "user_type": role,
        "assigned_program_ids": [],
    }
    record.update(changes)
    return database.save_user(record)


def create_application(name, status, program_id, **extra):
    record = {
        "owner_id": extra.pop("owner_id", 2),
        "program_id": program_id,
        "applicant_name": name,
        "full_name": name,
        "email": "demo@example.test",
        "degree_name": "Software Engineering",
        "degree_program": "Software Engineering",
        "campus": extra.pop("campus", "main"),
        "term": extra.pop("term", "Fall 2027"),
        "status": status,
        "fields": {},
        **extra,
    }
    return database.save_application(record)


def test_manage_users_retrieves_real_accounts_and_searches(admin_client):
    client, _, _ = admin_client
    advisor_id = create_account(
        "taylor", role="advisor",
        first_name="Taylor", last_name="Advisor",
    )
    create_account("avery", role="applicant")
    response = client.get(
        "/administrator/manage-users",
        params={"q": "taylor", "user_type": "advisor"},
    )
    assert response.status_code == 200
    assert "Taylor Advisor" in " ".join(response.text.split())
    assert "Avery Test" not in response.text
    assert "1 of 1 shown" in response.text
    assert 'value="advisor"' in response.text
    assert response.headers["cache-control"] == "no-store"

    selected = client.get(
        "/administrator/manage-users",
        params={"user": advisor_id, "q": "taylor", "user_type": "advisor"},
    )
    assert selected.status_code == 200
    assert 'data-user-id="' + str(advisor_id) + '"' in selected.text
    assert "manage-users.js" in selected.text
    assert "Assigned Degree Programs" in selected.text


def test_manage_users_persists_edits_through_existing_api(admin_client):
    client, _, program_id = admin_client
    advisor_id = create_account("taylor", role="advisor")
    response = client.patch(f"/api/users/{advisor_id}", json={
        "first_name": "Updated",
        "user_type": "advisor",
        "assigned_program_ids": [program_id],
    })
    assert response.status_code == 200, response.text
    persisted = next(u for u in database.users() if u["id"] == advisor_id)
    assert persisted["first_name"] == "Updated"
    assert persisted["assigned_program_ids"] == [program_id]
    response = client.get(
        "/administrator/manage-users", params={"user": advisor_id}
    )
    assert "Updated Test" in " ".join(response.text.split())
    assert 'value="' + str(program_id) + '"' in response.text


def test_manage_users_pagination_and_permissions(admin_client):
    client, actor, _ = admin_client
    for i in range(17):
        create_account(f"student{i:02d}")
    response = client.get("/administrator/manage-users")
    assert response.status_code == 200
    assert "Page 1 of 2" in response.text
    assert "Next" in response.text
    second = client.get("/administrator/manage-users", params={"page": 2})
    assert second.status_code == 200
    assert "Page 2 of 2" in second.text
    assert "Previous" in second.text

    actor["user_type"] = "applicant"
    assert client.get("/administrator/manage-users").status_code == 403
    assert client.get("/administrator/reports").status_code == 403
    assert client.get("/administrator/reports.csv").status_code == 403


def test_reports_use_real_sqlite_records_and_saved_program_decision(admin_client):
    client, _, program_id = admin_client
    in_review = create_application("Maya Thompson", "In Review", program_id)
    create_application("Olivia Reed", "Accepted", program_id)
    create_application("Avery Bennett", "Submitted", program_id)

    with database.connect() as connection:
        graduate_college.ensure_tables(connection)
        connection.execute(
            """INSERT INTO graduate_college_decisions
            (application_id, advisor_id, decision, rationale)
            VALUES (?, 1, 'Recommend', 'Strong application')""",
            (in_review,),
        )

    current = client.get(
        "/administrator/reports",
        params={"report_type": "current-applicants", "generate": "1"},
    )
    assert current.status_code == 200
    assert "2 records found." in " ".join(current.text.split())
    assert "Maya Thompson" in current.text
    assert "Avery Bennett" in current.text
    assert "Olivia Reed" not in current.text
    assert "Recommend" in current.text

    history = client.get(
        "/administrator/reports",
        params={"report_type": "applicant-status", "generate": "1"},
    )
    assert history.status_code == 200
    assert "3 records found." in " ".join(history.text.split())
    assert "Olivia Reed" in history.text
    assert "Accepted" in history.text

    filtered = client.get(
        "/administrator/reports",
        params={"report_type": "applicant-status", "status": "In Review",
                "decision": "Recommend", "campus": "Main", "generate": "1"},
    )
    assert "1 record found." in " ".join(filtered.text.split())
    assert "Maya Thompson" in filtered.text
    assert "Olivia Reed" not in filtered.text


def test_report_csv_matches_filters_and_updates_on_reload(admin_client):
    client, _, program_id = admin_client
    app_id = create_application("Avery Bennett", "Submitted", program_id)
    create_application("=BADFORMULA()", "Denied", program_id)

    csv_response = client.get(
        "/administrator/reports.csv",
        params={"report_type": "applicant-status", "status": "Denied"},
    )
    assert csv_response.status_code == 200
    rows = list(csv.reader(io.StringIO(csv_response.text)))
    assert len(rows) == 2
    assert rows[1][0] == "'=BADFORMULA()"
    assert rows[1][4] == "Denied"
    assert "attachment;" in csv_response.headers["content-disposition"]

    record = database.get_application(app_id)
    record["status"] = "In Review"
    database.save_application(record, app_id)

    filtered = client.get(
        "/administrator/reports",
        params={"report_type": "applicant-status", "status": "In Review",
                "generate": "1"},
    )
    assert "Avery Bennett" in filtered.text
    assert "1 record found." in " ".join(filtered.text.split())
