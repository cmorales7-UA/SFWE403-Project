"""Verify degree program forms read the database and expose wired controls."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.clients import database
from frontend.routes import degree_programs


@pytest.fixture
def degree_client(tmp_path, monkeypatch):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "degree-pages.sqlite3"))
    identity = {"id": 1, "user_type": "administrator"}
    monkeypatch.setattr(
        degree_programs.accounts, "session_user", lambda token: identity
    )
    app = FastAPI()
    app.include_router(degree_programs.router)
    return TestClient(app), identity


def sample_program(name="Software Engineering"):
    return {
        "degree_name": name,
        "degree_level": "masters",
        "degree_college": "College of Engineering",
        "degree_description": "Research and development",
        "campus_offered": ["main", "online"],
        "terms_offered": ["Fall 2027", "Spring 2028"],
        "degree_requirements": "Bachelor degree",
        "application_deadline": "2027-04-01",
        "application_fee": "90.00",
        "program_contact": "graduate@example.test",
    }


def test_create_page_includes_persistent_submit_handler(degree_client):
    client, _, = degree_client
    response = client.get("/administrator/create-degree-program")
    assert response.status_code == 200
    assert 'data-mode="create"' in response.text
    assert "degree-program-management.js" in response.text
    assert "Create Degree Program" in response.text


def test_modify_page_reads_saved_program_and_refreshes(degree_client):
    client, _ = degree_client
    program_id = database.save_program(sample_program())
    page = client.get("/administrator/modify-degree-program")
    assert page.status_code == 200
    assert "Software Engineering" in page.text
    assert 'data-mode="modify"' in page.text

    response = client.get(
        "/administrator/modify-degree-program",
        params={"degree_id": program_id},
    )
    assert response.status_code == 200
    assert 'data-program-id="' + str(program_id) + '"' in response.text
    assert 'value="Software Engineering"' in response.text
    assert "College of Engineering" in response.text
    assert 'value="main"' in response.text

    changed = database.get_application(-1)  # No application is required.
    assert changed is None
    updated = dict(sample_program(), degree_description="New degree description")
    database.save_program(updated, program_id)
    reloaded = client.get(
        "/administrator/modify-degree-program",
        params={"degree_id": program_id},
    )
    assert "New degree description" in reloaded.text
    assert "Research and development" not in reloaded.text


def test_unknown_program_and_role_rules(degree_client):
    client, actor = degree_client
    assert client.get(
        "/administrator/modify-degree-program", params={"degree_id": 999}
    ).status_code == 404

    actor["user_type"] = "applicant"
    assert client.get("/administrator/create-degree-program").status_code == 403
    assert client.get("/administrator/modify-degree-program").status_code == 403

    actor["user_type"] = "advisor"
    assert client.get("/advisor/create-degree-program").status_code == 200
    assert client.get("/advisor/modify-degree-program").status_code == 200
