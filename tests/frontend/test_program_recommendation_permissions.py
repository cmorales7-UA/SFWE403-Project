"""SRS 9.4.5: program decisions belong to the Advisor, not Administrator."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.clients import database
from backend.routes.api import router as api_router
from backend.service import accounts
from frontend.routes import reviews


@pytest.fixture
def setup_permissions(tmp_path, monkeypatch):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "recommendation-test.sqlite3"))
    se = database.save_program({"degree_name": "Software Engineering"})
    cs = database.save_program({"degree_name": "Computer Science"})
    people = {}
    for username, role, programs in (
        ("taylor.bennett", "advisor", [se]),
        ("morgan.chen", "advisor", [cs]),
        ("alex.morgan", "administrator", []),
    ):
        people[username] = database.save_user({
            "username": username,
            "email": f"{username}@arizona.edu",
            "first_name": username.split(".")[0].title(),
            "last_name": username.split(".")[1].title(),
            "user_type": role,
            "assigned_program_ids": programs,
        })

    application = database.save_application({
        "owner_id": 52,
        "program_id": se,
        "applicant_name": "Sophia Martinez",
        "full_name": "Sophia Martinez",
        "degree_program": "Software Engineering",
        "degree_name": "Software Engineering",
        "campus": "main",
        "term": "Fall 2027",
        "status": "In Review",
        "fields": {"full_name": "Sophia Martinez"},
        "review": {"review_comments": "Reviewed by the program advisor."},
    })

    acting = {"user_id": people["taylor.bennett"]}
    monkeypatch.setattr(
        accounts, "session_user",
        lambda token: next(user for user in database.users()
                           if user["id"] == acting["user_id"]),
    )
    app = FastAPI()
    app.include_router(reviews.router)
    app.include_router(api_router)
    return TestClient(app), people, acting, application


def test_advisor_sees_prominent_program_recommendations_navigation(setup_permissions):
    client, users, acting, app_id = setup_permissions
    page = client.get(f"/advisor/application-review?application={app_id}")
    assert page.status_code == 200
    assert "Program Recommendations" in page.text
    assert "Final Program Recommendation" in page.text
    assert f"/advisor/graduate-college?application={app_id}" in page.text
    assert "Save Preliminary Review" in page.text
    assert "Communicate with Applicant" in page.text

    destination = client.get("/advisor/graduate-college", params={"application": app_id})
    assert destination.status_code == 200
    assert "Final Program Recommendation" in destination.text
    assert 'id="gc-decision-form"' in destination.text
    assert 'id="gc-save-decision"' in destination.text
    assert 'id="gc-send-notification"' in destination.text

    # The sidebar contains the entry only once and no longer groups it with degree creation.
    assert destination.text.count('href="/advisor/graduate-college"') == 1


def test_advisor_can_save_program_decision_to_database(setup_permissions):
    client, people, acting, app_id = setup_permissions
    route = f"/api/graduate-college/applications/{app_id}/decision"
    payload = {"decision": "Recommend", "rationale": "Review complete."}

    saved = client.put(route, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["decision"]["decision"] == "Recommend"
    assert saved.json()["decision"]["advisor_id"] == people["taylor.bennett"]

    # New HTTP request reads persistent values rather than browser-only state.
    refreshed = client.get(f"/api/graduate-college/applications/{app_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["decision"]["rationale"] == "Review complete."


def test_administrator_can_view_but_not_edit_advisor_recommendation(setup_permissions):
    client, people, acting, app_id = setup_permissions
    endpoint = f"/api/graduate-college/applications/{app_id}/decision"
    payload = {"decision": "Deny", "rationale": "Advisor's saved decision."}
    assert client.put(endpoint, json=payload).status_code == 200

    acting["user_id"] = people["alex.morgan"]
    page = client.get(f"/administrator/application-review?application={app_id}")
    assert page.status_code == 200
    assert "Advisor Program Recommendation" in page.text
    assert "Advisor's saved decision." in page.text
    assert "Deny" in page.text
    assert "Open Admissions Processing" in page.text
    assert 'id="recommendation"' not in page.text
    assert 'name="recommendation"' not in page.text
    assert "Save Review" not in page.text

    # Directly calling the Advisor endpoint is also forbidden to Administrator.
    forbidden = client.put(
        endpoint,
        json={"decision": "Recommend", "rationale": "Unauthorized change"},
    )
    assert forbidden.status_code == 403
    acting["user_id"] = people["taylor.bennett"]
    assert client.get(f"/api/graduate-college/applications/{app_id}").json()["decision"]["decision"] == "Deny"


def test_advisor_cannot_edit_unassigned_program(setup_permissions):
    client, people, acting, app_id = setup_permissions
    acting["user_id"] = people["morgan.chen"]
    response = client.put(
        f"/api/graduate-college/applications/{app_id}/decision",
        json={"decision": "Defer", "rationale": "Unassigned program"},
    )
    assert response.status_code == 403
    page = client.get(f"/advisor/application-review?application={app_id}")
    assert page.status_code == 403
