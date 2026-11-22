"""Integration tests for live application filters and role authorization."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.clients import database
from backend.service import graduate_college
from frontend.routes import application_filters


@pytest.fixture
def setup_filter_app(tmp_path, monkeypatch):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "filters.sqlite3"))
    program_se = database.save_program({
        "degree_name": "Software Engineering",
        "campus_offered": ["main", "online"],
        "terms_offered": ["Fall 2027", "Spring 2028"],
    })
    program_cs = database.save_program({
        "degree_name": "Computer Science",
        "campus_offered": ["main"],
        "terms_offered": ["Fall 2027"],
    })

    def add_app(name, program, status, campus, fields=None):
        record = {
            "owner_id": len(database.applications()) + 1,
            "program_id": program,
            "applicant_name": name,
            "full_name": name,
            "degree_name": (
                "Software Engineering" if program == program_se
                else "Computer Science"
            ),
            "degree_program": (
                "Software Engineering" if program == program_se
                else "Computer Science"
            ),
            "term": "Fall 2027",
            "campus": campus,
            "status": status,
            "fields": fields or {},
        }
        return database.save_application(record)

    avery_id = add_app(
        "Avery Bennett", program_se, "Submitted", "main",
        {"legal_residence_country": "United States", "gender": "Male"},
    )
    maya_id = add_app(
        "Maya Thompson", program_se, "In Review", "online",
        {"legal_residence_country": "Mexico", "gender": "Female"},
    )
    jordan_id = add_app(
        "Jordan Rivera", program_cs, "In Process", "main",
        {"legal_residence_country": "United States"},
    )

    with database.connect() as db:
        graduate_college.ensure_tables(db)
        db.execute(
            """INSERT INTO graduate_college_decisions
            (application_id, advisor_id, decision, rationale)
            VALUES (?, 10, 'Recommend', 'Strong application')""",
            (maya_id,),
        )

    identity = {
        "id": 10, "user_type": "administrator",
        "assigned_program_ids": [program_se],
    }
    monkeypatch.setattr(
        application_filters.accounts, "session_user",
        lambda token: identity,
    )
    app = FastAPI()
    app.include_router(application_filters.router)
    client = TestClient(app)
    return client, identity, {
        "se": program_se, "cs": program_cs,
        "avery": avery_id, "maya": maya_id, "jordan": jordan_id,
    }


def test_administrator_sees_all_database_applications_and_filter_options(setup_filter_app):
    client, _, _ = setup_filter_app
    response = client.get("/administrator/filter-applications")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    for name in ("Avery Bennett", "Maya Thompson", "Jordan Rivera"):
        assert name in response.text
    assert "3 applications available to your account." in " ".join(response.text.split())
    assert 'value="Software Engineering"' in response.text
    assert 'value="Computer Science"' in response.text
    assert 'value="In Process"' in response.text
    assert 'value="In Review"' in response.text
    assert 'value="Submitted"' in response.text


def test_combined_filters_and_normalized_campus(setup_filter_app):
    client, _, _ = setup_filter_app
    response = client.get(
        "/administrator/filter-applications",
        params={
            "degree": "Software Engineering",
            "applicant_name": "maya",
            "gender": "Female",
            "country": "mex",
            "campus": "Online",
            "term": "Fall 2027",
            "status": "In Review",
            "decision": "Recommend",
        },
    )
    assert response.status_code == 200
    assert "1 application matching your selected filters." in " ".join(response.text.split())
    assert "Maya Thompson" in response.text
    assert "Avery Bennett" not in response.text
    assert "Jordan Rivera" not in response.text


def test_no_match_and_clear_filters(setup_filter_app):
    client, _, _ = setup_filter_app
    none = client.get(
        "/administrator/filter-applications",
        params={"gender": "Male", "status": "In Review"},
    )
    assert "No Matching Applications" in none.text
    assert "0 applications matching your selected filters." in " ".join(none.text.split())
    assert "3 applications available to your account." in " ".join(
        client.get("/administrator/filter-applications").text.split()
    )


def test_advisor_only_sees_assigned_programs(setup_filter_app):
    client, identity, _ = setup_filter_app
    identity["user_type"] = "advisor"
    response = client.get("/advisor/filter-applications")
    assert response.status_code == 200
    assert "Avery Bennett" in response.text
    assert "Maya Thompson" in response.text
    assert "Jordan Rivera" not in response.text
    assert 'value="Computer Science"' not in response.text
    assert "2 applications available to your account." in " ".join(response.text.split())

    denied = client.get("/administrator/filter-applications")
    assert denied.status_code == 403


def test_new_changes_show_on_next_request(setup_filter_app):
    client, _, ids = setup_filter_app
    original = database.get_application(ids["avery"])
    original["status"] = "In Review"
    database.save_application(original, ids["avery"])
    response = client.get(
        "/administrator/filter-applications",
        params={"status": "In Review"},
    )
    assert response.status_code == 200
    assert "Avery Bennett" in response.text
    assert "Maya Thompson" in response.text
    assert "Jordan Rivera" not in response.text


def test_unknown_gender_is_not_assumed(setup_filter_app):
    client, _, _ = setup_filter_app
    response = client.get(
        "/administrator/filter-applications",
        params={"gender": "Male"},
    )
    assert "Avery Bennett" in response.text
    assert "Jordan Rivera" not in response.text
