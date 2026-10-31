"""Acceptance tests for application ownership, advisor scope, review, and communication."""
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.clients import database
from backend.service import mailer


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "gdas-test.sqlite3"))
    with TestClient(app) as browser:
        yield browser


def register(client, name):
    value = {
        "username": name, "password": "Test1234!",
        "first_name": name, "last_name": "Student",
        "email": f"{name}@example.test", "phone": "5551234567",
        "security_question_1": "Pet?", "security_answer_1": "Dog",
        "security_question_2": "School?", "security_answer_2": "UA"
    }
    response = client.post("/api/users", json=value)
    assert response.status_code == 201
    return response.json()["id"]


def login(client, name, role=None, programs=None):
    if role:
        user = next(u for u in database.users() if u["username"] == name)
        uid = user.pop("id")
        user["user_type"] = role
        if programs is not None:
            user["assigned_program_ids"] = programs
        database.save_user(user, uid)
    assert client.post("/api/login", json={"username": name, "password": "Test1234!"}).status_code == 200


def program(client):
    body = {
        "degree_name": "Software Engineering", "degree_level": "masters",
        "degree_college": "Engineering", "degree_description": "Program",
        "campus_offered": ["main"], "terms_offered": ["Fall 2027"],
        "degree_requirements": "Bachelor degree", "application_deadline": "2027-01-15",
        "application_fee": "90.00", "program_contact": "grad@example.com"
    }
    return client.post("/api/programs", json=body).json()["id"]


def setup(client):
    admin = register(client, "admin")
    applicant = register(client, "student")
    other = register(client, "other")
    advisor = register(client, "advisor")
    login(client, "admin", "administrator")
    degree_id = program(client)
    login(client, "advisor", "advisor", [degree_id])
    return admin, applicant, other, advisor, degree_id


def create(client, degree_id):
    login(client, "student")
    fields = {
        "full_name": "Student Student", "reference_1_name": "Professor",
        "reference_1_contact": "prof@example.test"
    }
    response = client.post("/api/applications", json={
        "program_id": degree_id, "campus": "main", "term": "Fall 2027",
        "fields": fields, "submitted": True
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_ownership_and_advisor_program_scope(client):
    _, student_id, _, _, degree_id = setup(client)
    assert client.get("/api/applications").status_code == 200
    application_id = create(client, degree_id)
    assert client.get(f"/api/applications/{application_id}").status_code == 200
    assert len(client.get("/api/applications").json()) == 1

    login(client, "other")
    assert client.get("/api/applications").json() == []
    assert client.get(f"/api/applications/{application_id}").status_code == 403
    assert client.patch(f"/api/applications/{application_id}", json={"fields": {"full_name": "Stolen"}}).status_code == 403

    login(client, "advisor")
    assert len(client.get("/api/applications").json()) == 1
    assert client.patch(f"/api/applications/{application_id}", json={"fields": {"mailing_address": "Tucson"}}).status_code == 200

    login(client, "admin")
    assert len(client.get("/api/applications").json()) == 1
    assert client.patch(f"/api/applications/{application_id}", json={"fields": {"mailing_address": "Yuma"}}).status_code == 200
    assert client.patch("/api/users/4", json={"assigned_program_ids": []}).status_code == 200

    login(client, "advisor")
    assert client.get("/api/applications").json() == []
    assert client.get(f"/api/applications/{application_id}").status_code == 403
    assert client.patch(f"/api/applications/{application_id}", json={"fields": {"mailing_address": "Bad"}}).status_code == 403

    login(client, "student")
    assert client.get(f"/api/applications/{application_id}").json()["owner_id"] == student_id
    assert client.patch(f"/api/applications/{application_id}", json={"fields": {"owner_id": "999"}}).status_code == 200
    assert database.get_application(application_id)["owner_id"] == student_id


def test_preliminary_review_notification_and_reference_credentials(client, monkeypatch):
    _, _, _, _, degree_id = setup(client)
    application_id = create(client, degree_id)
    delivered = []
    monkeypatch.setattr(mailer, "send_email", lambda to, subject, body: delivered.append((to, subject, body)))
    login(client, "advisor")
    response = client.post(f"/api/applications/{application_id}/preliminary-review", json={
        "review_comments": "Private note", "missing_information": "Please provide GPA."
    })
    assert response.status_code == 200
    assert response.json()["status"] == "Needs Information"
    assert client.post(f"/api/applications/{application_id}/request-information").status_code == 200
    assert "Please provide GPA" in delivered[-1][2]

    request = client.post(f"/api/applications/{application_id}/recommendation-requests",
                          json={"reference_number": 1})
    assert request.status_code == 200
    assert "System-assigned login name:" in delivered[-1][2]
    assert "Authorization code:" in delivered[-1][2]
    assert "Authorization code:" not in str(request.json())
    assert len(database.recommendation_requests(application_id)) == 1

    login(client, "student")
    student_view = client.get(f"/api/applications/{application_id}").json()
    assert "review" not in student_view


def test_email_permissions_and_unconfigured_delivery(client, monkeypatch):
    _, _, _, _, degree_id = setup(client)
    application_id = create(client, degree_id)
    message = {"subject": "Application status", "body": "Please update your application."}
    login(client, "student")
    assert client.post(f"/api/applications/{application_id}/messages", json=message).status_code == 403
    login(client, "admin")
    monkeypatch.delenv("GDAS_SMTP_HOST", raising=False)
    monkeypatch.delenv("GDAS_SMTP_FROM", raising=False)
    assert client.post(f"/api/applications/{application_id}/messages", json=message).status_code == 503
    assert database.messages(application_id) == []
    delivered = []
    monkeypatch.setattr(mailer, "send_email", lambda to, sub, body: delivered.append((to, sub, body)))
    assert client.post(f"/api/applications/{application_id}/messages", json=message).status_code == 200
    assert delivered[0][0] == "student@example.test"
    assert len(database.messages(application_id)) == 1
