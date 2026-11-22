"""SRS 9.5.1: saved program questions appear on applications."""

from hashlib import sha256

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.clients import database
from backend.routes.api import router as api_router
from frontend.routes import applicant


def test_program_custom_question_is_displayed_and_answer_persists(
    monkeypatch, tmp_path,
):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "question.sqlite3"))
    user_id = database.save_user({
        "username": "testapplicant",
        "email": "testapplicant@example.test",
        "first_name": "Jordan",
        "last_name": "Rivera",
        "user_type": "applicant",
    })
    actor = next(user for user in database.users() if user["id"] == user_id)
    monkeypatch.setattr(applicant.accounts, "session_user", lambda token: actor)

    question = "Describe your capstone project."
    program_id = database.save_program({
        "degree_name": "Software Engineering",
        "degree_level": "masters",
        "degree_college": "College of Engineering",
        "degree_description": "Graduate engineering studies.",
        "campus_offered": ["main"],
        "terms_offered": ["Fall 2027"],
        "degree_requirements": "Bachelor's degree",
        "application_deadline": "2027-05-01",
        "application_fee": "90.00",
        "program_contact": "gdas.programs@arizona.edu",
        "custom_questions": [question],
        "sponsor_question": "Who is your faculty sponsor?",
    })

    app = FastAPI()
    app.include_router(applicant.router)
    app.include_router(api_router)
    client = TestClient(app)

    form = client.get(
        "/applicant/application", params={"degree_id": program_id}
    )
    assert form.status_code == 200
    assert question in form.text
    assert "Who is your faculty sponsor?" in form.text

    answer_key = "program_question_" + sha256(
        question.strip().casefold().encode("utf-8")
    ).hexdigest()[:12]
    assert f'name="{answer_key}"' in form.text

    response = client.post("/api/applications", json={
        "program_id": program_id,
        "campus": "main",
        "term": "Fall 2027",
        "submitted": False,
        "fields": {
            "full_name": "Jordan Rivera",
            answer_key: "I built an automated chamber control system.",
        },
    })
    assert response.status_code == 201, response.text
    saved = database.get_application(response.json()["id"])
    assert saved["fields"][answer_key] == (
        "I built an automated chamber control system."
    )
