"""SRS 9.5.1 acceptance tests using a temporary SQLite database."""

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.clients import database
from backend.service import accounts


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "programs.sqlite3"))
    users = {}
    for role, name in (
        ("administrator", "admin"),
        ("advisor", "advisor_one"),
        ("advisor", "advisor_two"),
        ("applicant", "applicant"),
    ):
        identifier = database.save_user({
            "username": name,
            "first_name": name,
            "last_name": "Sample",
            "email": f"{name}@example.test",
            "user_type": role,
            "assigned_program_ids": [],
        })
        users[name] = identifier

    current = {"id": users["admin"]}
    monkeypatch.setattr(
        accounts,
        "session_user",
        lambda token: next(
            user for user in database.users()
            if user["id"] == current["id"]
        ),
    )
    return TestClient(app), users, current


def program(advisors=None, **changes):
    value = {
        "degree_name": "Applied Software Engineering",
        "degree_level": "masters",
        "degree_college": "College of Engineering",
        "degree_description": "Advanced engineering study and research.",
        "degree_requirements": "Bachelor's degree and statement of purpose.",
        "other_requirements": "Resume and references.",
        "sponsor_question": "Do you have a faculty sponsor?",
        "ta_ra_question": "Describe any assistantship experience.",
        "funding_question": "Do you require funding?",
        "english_test_question": "English test date?",
        "english_score_question": "English proficiency score?",
        "custom_questions": [
            "Describe your capstone experience.",
            "What is your primary research interest?",
        ],
        "campus_offered": ["main", "online"],
        "terms_offered": ["Fall 2027", "Spring 2028"],
        "application_fee": "90.00",
        "resident_cost_per_unit": "650.00",
        "nonresident_cost_per_unit": "1500.00",
        "application_deadline": "2027-05-01",
        "program_contact": "gradprogram@example.test",
        "collaborating_advisor_ids": advisors or [],
    }
    value.update(changes)
    return value


def test_administrator_creates_all_required_fields_and_invites_advisor(system):
    client, users, current = system
    response = client.post("/api/programs", json=program([users["advisor_one"]]))
    assert response.status_code == 201, response.text

    saved = database.programs()[0]
    assert saved["degree_name"] == "Applied Software Engineering"
    assert saved["degree_level"] == "masters"
    assert saved["degree_college"] == "College of Engineering"
    assert saved["degree_description"].startswith("Advanced")
    assert saved["degree_requirements"].startswith("Bachelor")
    assert len(saved["custom_questions"]) == 2
    assert saved["campus_offered"] == ["main", "online"]
    assert saved["terms_offered"] == ["Fall 2027", "Spring 2028"]
    assert saved["resident_cost_per_unit"] == "650.00"
    assert saved["nonresident_cost_per_unit"] == "1500.00"
    assert saved["program_contact"] == "gradprogram@example.test"
    assert saved["collaborating_advisor_ids"] == [users["advisor_one"]]

    history = client.get(f"/api/programs/{saved['id']}/history")
    assert history.status_code == 200
    assert history.json()[0]["action"] == "created"
    assert history.json()[0]["actor_role"] == "administrator"


def test_advisor_participates_and_edits_are_audited(system):
    client, users, current = system
    created = client.post(
        "/api/programs", json=program([users["advisor_one"]])
    ).json()
    program_id = created["id"]

    current["id"] = users["advisor_one"]
    updated = program(
        [users["advisor_two"]],  # Advisor cannot grant access.
        degree_description="Updated program description by advisor.",
        nonresident_cost_per_unit="1625.00",
    )
    response = client.put(f"/api/programs/{program_id}", json=updated)
    assert response.status_code == 200, response.text
    assert response.json()["degree_description"] == updated["degree_description"]
    assert response.json()["collaborating_advisor_ids"] == [users["advisor_one"]]
    assert database.programs()[0]["nonresident_cost_per_unit"] == "1625.00"

    history = client.get(f"/api/programs/{program_id}/history").json()
    assert len(history) == 2
    assert history[0]["actor_role"] == "advisor"
    assert "nonresident_cost_per_unit" in history[0]["changed_fields"]

    current["id"] = users["advisor_two"]
    assert client.get(f"/api/programs/{program_id}").status_code == 404
    assert client.put(
        f"/api/programs/{program_id}", json=updated
    ).status_code == 404

    current["id"] = users["admin"]
    response = client.put(
        f"/api/programs/{program_id}",
        json=program([users["advisor_one"], users["advisor_two"]]),
    )
    assert response.status_code == 200
    current["id"] = users["advisor_two"]
    assert client.get(f"/api/programs/{program_id}").status_code == 200


def test_advisor_creation_assigns_new_program_for_future_management(system):
    client, users, current = system
    current["id"] = users["advisor_one"]
    response = client.post("/api/programs", json=program())
    assert response.status_code == 201, response.text
    program_id = response.json()["id"]
    assert response.json()["collaborating_advisor_ids"] == [users["advisor_one"]]
    advisor = next(user for user in database.users() if user["id"] == users["advisor_one"])
    assert program_id in advisor["assigned_program_ids"]
    assert client.get(f"/api/programs/{program_id}").status_code == 200


def test_program_validation_and_role_restrictions(system):
    client, users, current = system
    assert client.post(
        "/api/programs", json=program(resident_cost_per_unit=None)
    ).status_code == 422
    assert client.post(
        "/api/programs", json=program(nonresident_cost_per_unit="-1")
    ).status_code == 422
    assert client.post(
        "/api/programs", json=program(terms_offered=[])
    ).status_code == 422
    assert client.post(
        "/api/programs", json=program(advisors=[9999])
    ).status_code == 422
    assert client.post(
        "/api/programs", json=program(
            custom_questions=["Duplicate", "duplicate"]
        )
    ).status_code == 422

    current["id"] = users["applicant"]
    assert client.post("/api/programs", json=program()).status_code == 403
    assert client.get("/api/programs").status_code == 403


def test_legacy_update_preserves_tuition_and_custom_questions(system):
    client, users, current = system
    created = client.post("/api/programs", json=program()).json()
    previous = program()
    previous.pop("resident_cost_per_unit")
    previous.pop("nonresident_cost_per_unit")
    previous.pop("custom_questions")
    previous["degree_requirements"] = "Updated entry requirements."
    result = client.put(f"/api/programs/{created['id']}", json=previous)
    assert result.status_code == 200
    assert result.json()["resident_cost_per_unit"] == "650.00"
    assert len(result.json()["custom_questions"]) == 2
