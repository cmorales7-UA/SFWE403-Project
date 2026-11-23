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


def test_administrator_can_edit_original_review_form_and_preserve_advisor_route_permissions(setup_permissions):
    client, people, acting, app_id = setup_permissions
    endpoint = f"/api/graduate-college/applications/{app_id}/decision"
    payload = {"decision": "Deny", "rationale": "Advisor's saved decision."}
    assert client.put(endpoint, json=payload).status_code == 200

    acting["user_id"] = people["alex.morgan"]
    page = client.get(f"/administrator/application-review?application={app_id}")
    assert page.status_code == 200
    assert "Internal Review Comments" in page.text
    assert "Final Recommendation" in page.text
    assert "Recommendation Rationale" in page.text
    assert 'id="review_comments"' in page.text
    assert 'id="recommendation"' in page.text
    assert 'id="advisor_rationale"' in page.text
    assert 'data-decision-version="1"' in page.text
    assert "Save Review" in page.text
    assert "Save Notes" not in page.text
    assert "Advisor Program Recommendation" not in page.text

    # The Advisor's endpoint remains Advisor-only. Administrators use the
    # separately authorized and audited Graduate College edit endpoint.
    forbidden = client.put(
        endpoint,
        json={"decision": "Recommend", "rationale": "Unauthorized change"},
    )
    assert forbidden.status_code == 403
    acting["user_id"] = people["taylor.bennett"]
    assert client.get(f"/api/graduate-college/applications/{app_id}").json()["decision"]["decision"] == "Deny"


def test_admin_review_form_saves_all_original_fields_and_advisor_sees_changes(setup_permissions):
    client, people, acting, app_id = setup_permissions
    advisor_endpoint = f"/api/graduate-college/applications/{app_id}/decision"
    assert client.put(
        advisor_endpoint,
        json={"decision": "Recommend", "rationale": "Original rationale"},
    ).status_code == 200

    acting["user_id"] = people["alex.morgan"]
    endpoint = f"/api/applications/{app_id}/graduate-college-review"
    payload = {
        "review_comments": "Updated after document verification.",
        "decision": "Deny",
        "rationale": "Admission requirements not met.",
        "decision_version": 1,
    }
    result = client.put(endpoint, json=payload)
    assert result.status_code == 200, result.text
    assert result.json()["review"]["review_comments"] == payload["review_comments"]
    assert result.json()["decision_version"] == 2
    assert result.json()["notification_required"] is True

    # Refresh the Administrator page and verify the exact original form fields
    # contain the database values rather than stale frontend state.
    page = client.get(f"/administrator/application-review?application={app_id}")
    assert "Updated after document verification." in page.text
    assert "Admission requirements not met." in page.text
    assert 'data-decision-version="2"' in page.text

    current = database.get_application(app_id)
    assert current["review"]["review_comments"] == payload["review_comments"]

    with database.connect() as db:
        decision = db.execute(
            "SELECT advisor_id, decision, rationale, version FROM graduate_college_decisions WHERE application_id=?",
            (app_id,),
        ).fetchone()
        assert decision["advisor_id"] == people["taylor.bennett"]
        assert decision["decision"] == "Deny"
        assert decision["rationale"] == payload["rationale"]
        assert decision["version"] == 2
        history = db.execute(
            "SELECT * FROM graduate_college_admin_edit_history WHERE application_id=?",
            (app_id,),
        ).fetchall()
        assert len(history) == 1
        assert history[0]["administrator_id"] == people["alex.morgan"]
        assert history[0]["previous_decision"] == "Recommend"
        assert history[0]["updated_decision"] == "Deny"

    # Stale browser submissions cannot silently replace the latest decision.
    stale = client.put(endpoint, json={**payload, "rationale": "Outdated browser edit"})
    assert stale.status_code == 409

    acting["user_id"] = people["taylor.bennett"]
    refreshed = client.get(f"/api/graduate-college/applications/{app_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["decision"]["decision"] == "Deny"
    assert refreshed.json()["decision"]["rationale"] == payload["rationale"]

    # An Advisor still cannot call the Administrator's edit route.
    assert client.put(endpoint, json=payload).status_code == 403


def test_administrator_cannot_create_advisor_decision_or_edit_finalized_application(setup_permissions):
    client, people, acting, app_id = setup_permissions
    acting["user_id"] = people["alex.morgan"]
    endpoint = f"/api/applications/{app_id}/graduate-college-review"
    proposal = {
        "review_comments": "Reviewed",
        "decision": "Recommend",
        "rationale": "Proposed decision",
    }
    assert client.put(endpoint, json=proposal).status_code == 409
    assert client.put(endpoint, json={"review_comments": "Reviewed"}).status_code == 200
    record = database.get_application(app_id)
    assert record["review"]["review_comments"] == "Reviewed"

    record["status"] = "Accepted"
    database.save_application(record, app_id)
    assert client.put(endpoint, json={"review_comments": "Post decision"}).status_code == 409
    assert database.get_application(app_id)["review"]["review_comments"] == "Reviewed"
    page = client.get(f"/administrator/application-review?application={app_id}")
    assert "Save Review" not in page.text



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


def test_admin_review_notes_persist_without_changing_advisor_decision(setup_permissions):
    client, people, acting, app_id = setup_permissions
    advisor_url = f"/api/graduate-college/applications/{app_id}/decision"
    saved = client.put(
        advisor_url,
        json={"decision": "Recommend", "rationale": "Advisor approved."},
    )
    assert saved.status_code == 200

    acting["user_id"] = people["alex.morgan"]
    endpoint = f"/api/applications/{app_id}/graduate-college-review"
    result = client.put(endpoint, json={"notes": "Reviewed supporting documents."})
    assert result.status_code == 200, result.text
    assert result.json()["review"]["graduate_college_notes"] == "Reviewed supporting documents."
    assert result.json()["review"]["review_comments"] == "Reviewed by the program advisor."
    assert result.json()["review"]["graduate_college_updated_by"] == people["alex.morgan"]

    page = client.get(f"/administrator/application-review?application={app_id}")
    assert page.status_code == 200
    assert "Internal Review Comments" in page.text
    assert "Save Review" in page.text
    # Existing Graduate College notes remain in SQLite even though the
    # original form displays the shared preliminary review comments instead.
    assert database.get_application(app_id)["review"]["graduate_college_notes"] == "Reviewed supporting documents."

    result = client.put(endpoint, json={"notes": "Documents verified."})
    assert result.status_code == 200
    assert result.json()["review"]["graduate_college_notes"] == "Documents verified."
    assert client.get(f"/api/applications/{app_id}").json()["review"]["graduate_college_notes"] == "Documents verified."

    acting["user_id"] = people["taylor.bennett"]
    assert client.put(endpoint, json={"notes": "Unauthorized"}).status_code == 403
    advisor_app = client.get(f"/api/applications/{app_id}")
    assert advisor_app.status_code == 200
    assert "graduate_college_notes" not in advisor_app.json()["review"]
    current_recommendation = client.get(f"/api/graduate-college/applications/{app_id}")
    assert current_recommendation.json()["decision"]["decision"] == "Recommend"
    assert current_recommendation.json()["decision"]["rationale"] == "Advisor approved."

    acting["user_id"] = people["alex.morgan"]
    record = database.get_application(app_id)
    record["status"] = "Accepted"
    database.save_application(record, app_id)
    assert client.put(endpoint, json={"notes": "Late edit"}).status_code == 409
    assert database.get_application(app_id)["review"]["graduate_college_notes"] == "Documents verified."
