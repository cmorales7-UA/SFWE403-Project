"""ConOps SRS 9.5.2–9.5.5: authenticated end-to-end admissions acceptance tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from backend.clients import database
from backend.service import accounts, admissions, graduate_college, mailer


def sample_fields():
    return {
        "full_name": "Avery Bennett",
        "preferred_pronoun": "They/them",
        "date_of_birth": "2000-06-04",
        "mailing_address": "1400 E University Blvd, Tucson, AZ",
        "email_address": "avery.bennett@arizona.edu",
        "phone": "5205550102",
        "citizenship": "United States",
        "country_of_birth": "United States",
        "legal_residence_country": "United States",
        "visa": "",
        "military_affiliation": "No",
        "previous_ua_affiliation": "No",
        "resident_tuition_eligibility": "Yes",
        "education_degree_name": "BS",
        "university_name": "Southwest University",
        "degree_type": "Bachelors",
        "degree_name": "Software Engineering",
        "total_credits": "120",
        "degree_start_date": "2018-08-20",
        "degree_received_date": "2022-05-14",
        "cumulative_gpa": "3.75",
        "ethnicity": "Hispanic",
    }


@pytest.fixture
def environment(tmp_path, monkeypatch):
    path = tmp_path / "admissions.sqlite3"
    monkeypatch.setenv("GDAS_DB_PATH", str(path))

    users = {}
    for username, role, first, last, assigned in (
        ("alex.morgan", "administrator", "Alex", "Morgan", []),
        ("taylor.bennett", "advisor", "Taylor", "Bennett", [1]),
        ("avery.bennett", "applicant", "Avery", "Bennett", []),
        ("maya.thompson", "applicant", "Maya", "Thompson", []),
    ):
        uid = database.save_user({
            "username": username,
            "email": f"{username}@arizona.edu",
            "first_name": first,
            "last_name": last,
            "net_id": username.replace(".", ""),
            "phone": "5205550102",
            "user_type": role,
            "assigned_program_ids": assigned,
        })
        users[role if role in ("administrator", "advisor") else username] = uid

    program_id = database.save_program({
        "degree_name": "Software Engineering",
        "degree_level": "masters",
        "degree_college": "College of Engineering",
        "degree_description": "Software systems",
        "degree_requirements": "Bachelor degree and references",
        "program_contact": "gdas.programs@arizona.edu",
        "resident_cost_per_unit": "650.00",
        "nonresident_cost_per_unit": "1500.00",
    })
    application_id = database.save_application({
        "owner_id": users["avery.bennett"],
        "program_id": program_id,
        "degree_name": "Software Engineering",
        "degree_program": "Software Engineering",
        "full_name": "Avery Bennett",
        "applicant_name": "Avery Bennett",
        "email": "avery.bennett@arizona.edu",
        "campus": "main",
        "term": "Fall 2027",
        "status": "In Review",
        "fields": sample_fields(),
        "review": {},
    })

    identity = {"id": users["administrator"]}
    monkeypatch.setattr(
        accounts, "session_user",
        lambda token: next(u for u in database.users() if u["id"] == identity["id"]),
    )
    sent = []
    monkeypatch.setattr(
        mailer, "send_email",
        lambda address, subject, body: sent.append((address, subject, body)),
    )
    return TestClient(app), identity, users, application_id, sent


def act_as(identity, users, target):
    identity["id"] = users[target]


def deliver_advisor_recommendation(client, identity, users, application_id, decision):
    act_as(identity, users, "advisor")
    saved = client.put(
        f"/api/graduate-college/applications/{application_id}/decision",
        json={"decision": decision, "rationale": "Committee review complete."},
    )
    assert saved.status_code == 200, saved.text

    sent = client.post(
        f"/api/graduate-college/applications/{application_id}/notifications",
        json={"administrator_id": users["administrator"]},
    )
    assert sent.status_code == 200, sent.text
    act_as(identity, users, "administrator")


def test_srs_952_formal_acceptance_email_and_printable_letter(environment):
    client, identity, users, application_id, emails = environment
    deliver_advisor_recommendation(client, identity, users, application_id, "Recommend")
    assert len(emails) == 1

    issued = client.post(f"/api/admissions/{application_id}/official-notice")
    assert issued.status_code == 200, issued.text
    assert issued.json()["application_status"] == "Accepted"
    assert issued.json()["notice"]["decision"] == "Accepted"
    assert issued.json()["notice"]["state"] == "sent"
    assert len(emails) == 2
    assert emails[1][0] == "avery.bennett@arizona.edu"
    assert "Fall 2027" in emails[1][2]
    assert "Software Engineering" in emails[1][2]
    assert "College of Engineering" in emails[1][2]

    page = client.get(f"/administrator/admissions/{application_id}/letter")
    assert page.status_code == 200
    assert "Print Letter" in page.text
    assert "Graduate College" in page.text
    assert "Graduate Admission Decision" in page.text
    assert "Fall 2027" in page.text

    duplicate = client.post(f"/api/admissions/{application_id}/official-notice")
    assert duplicate.status_code == 409
    assert len(emails) == 2
    assert database.get_application(application_id)["status"] == "Accepted"

    # Student record can be created after acceptance, before intent to matriculate.
    assert issued.json()["intent"] is None


def test_srs_953_954_applicant_intent_and_registrar_simulation(environment):
    client, identity, users, application_id, _ = environment
    deliver_advisor_recommendation(client, identity, users, application_id, "Recommend")
    assert client.post(f"/api/admissions/{application_id}/process-intent").status_code == 409
    assert client.post(f"/api/admissions/{application_id}/official-notice").status_code == 200
    assert client.post(f"/api/admissions/{application_id}/process-intent").status_code == 409

    act_as(identity, users, "avery.bennett")
    first = client.post(f"/api/admissions/{application_id}/intent")
    assert first.status_code == 201, first.text
    assert first.json()["application_status"] == "Accepted"
    assert first.json()["intent"]["processed_at"] is None
    assert client.post(f"/api/admissions/{application_id}/intent").status_code == 409

    page = client.get(f"/applicant/admission-offer?application_id={application_id}")
    assert page.status_code == 200
    assert "Your intent was received" in page.text

    act_as(identity, users, "administrator")
    processed = client.post(f"/api/admissions/{application_id}/process-intent")
    assert processed.status_code == 200, processed.text
    assert processed.json()["application_status"] == "Intent to Matriculate"
    assert processed.json()["intent"]["processed_at"]
    assert processed.json()["student_record_id"] is None
    assert client.post(f"/api/admissions/{application_id}/process-intent").status_code == 409

    notification = client.get(
        f"/api/admissions/{application_id}/registrar-simulation"
    )
    assert notification.status_code == 200
    assert notification.json()["term"] == "Fall 2027"
    assert "SIMULATION ONLY" in notification.json()["notice_text"]
    assert "Intent to Matriculate" in notification.json()["notice_text"]
    saved = client.get(
        f"/administrator/admissions/{application_id}/registrar-notification"
    )
    assert saved.status_code == 200
    assert "Fall 2027" in saved.text
    assert "No connection to the actual University Registrar" in saved.text


def test_srs_955_create_complete_student_record_with_transcript_before_intent(environment):
    client, identity, users, application_id, _ = environment
    deliver_advisor_recommendation(client, identity, users, application_id, "Recommend")
    assert client.post(f"/api/admissions/{application_id}/official-notice").status_code == 200

    required = client.post(
        f"/api/admissions/{application_id}/student-record",
        json={"tuition_classification": "resident"},
    )
    assert required.status_code == 422
    assert "official_transcripts" in required.json()["detail"]

    pdf_bytes = b"%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF"
    uploaded = client.post(
        f"/api/admissions/{application_id}/official-transcript",
        files={"official_transcript": ("official-transcript.pdf", pdf_bytes, "application/pdf")},
        data={"verified": "true"},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["transcript"]["filename"] == "official-transcript.pdf"

    created = client.post(
        f"/api/admissions/{application_id}/student-record",
        json={"tuition_classification": "resident"},
    )
    assert created.status_code == 201, created.text
    snapshot = created.json()
    assert snapshot["full_name"] == "Avery Bennett"
    assert snapshot["preferred_pronoun"] == "They/them"
    assert snapshot["country_of_birth"] == "United States"
    assert snapshot["military_affiliation"] == "No"
    assert snapshot["previous_ua_affiliation"] == "No"
    assert snapshot["tuition_classification"] == "resident"
    assert snapshot["tuition_amount_per_unit"] == "650.00"
    assert snapshot["net_id"] == "averybennett"
    assert snapshot["citizenship"] == "United States"
    assert snapshot["term"] == "Fall 2027"
    assert snapshot["campus"] == "main"
    assert snapshot["cumulative_gpa"] == "3.75"
    assert snapshot["education_history"][0]["institution"] == "Southwest University"
    assert snapshot["official_transcripts"]["status"] == "Verified copy on file"
    assert snapshot["ethnicity"] == "Hispanic"
    assert snapshot["record_created_at"]
    assert not snapshot["missing_verification_fields"]
    assert database.get_application(application_id)["status"] == "Accepted"

    same = client.get(f"/api/admissions/{application_id}/student-record")
    assert same.status_code == 200
    assert same.json()["id"] == created.json()["id"]
    assert client.post(
        f"/api/admissions/{application_id}/student-record",
        json={"tuition_classification": "nonresident"},
    ).status_code == 409

    post_creation_upload = client.post(
        f"/api/admissions/{application_id}/official-transcript",
        files={"official_transcript": ("replacement.pdf", pdf_bytes, "application/pdf")},
        data={"verified": "true"},
    )
    assert post_creation_upload.status_code == 409

    down = client.get(f"/api/admissions/{application_id}/official-transcript")
    assert down.status_code == 200
    assert down.content == pdf_bytes
    assert client.get(f"/administrator/admissions/{application_id}/student-record").status_code == 200


def test_srs_952_rejection_and_defer_do_not_matriculate(environment):
    client, identity, users, application_id, emails = environment
    deliver_advisor_recommendation(client, identity, users, application_id, "Deny")
    rejected = client.post(f"/api/admissions/{application_id}/official-notice")
    assert rejected.status_code == 200
    assert rejected.json()["application_status"] == "Denied"
    assert "not been accepted" in emails[-1][2]
    assert client.post(
        f"/api/admissions/{application_id}/student-record",
        json={"tuition_classification": "resident"},
    ).status_code == 409
    act_as(identity, users, "avery.bennett")
    assert client.post(f"/api/admissions/{application_id}/intent").status_code == 409


def test_srs_negative_permission_and_email_failure_does_not_finalize(environment, monkeypatch):
    client, identity, users, application_id, emails = environment
    deliver_advisor_recommendation(client, identity, users, application_id, "Recommend")
    act_as(identity, users, "avery.bennett")
    assert client.post(f"/api/admissions/{application_id}/official-notice").status_code == 403
    assert client.get(f"/api/admissions/{application_id}/student-record").status_code == 403
    assert client.get(f"/administrator/admissions").status_code == 403
    assert client.post(
        f"/api/admissions/{application_id}/official-transcript",
        files={"official_transcript": ("x.pdf", b"%PDF-1.4", "application/pdf")},
        data={"verified": "true"},
    ).status_code == 403
    act_as(identity, users, "maya.thompson")
    assert client.post(f"/api/admissions/{application_id}/intent").status_code == 403
    assert client.get(f"/applicant/admission-offer?application_id={application_id}").status_code == 403

    act_as(identity, users, "administrator")
    from fastapi import HTTPException
    original_send = mailer.send_email
    monkeypatch.setattr(
        mailer, "send_email",
        lambda to, sub, body: (_ for _ in ()).throw(HTTPException(503, "SMTP unavailable")),
    )
    failed = client.post(f"/api/admissions/{application_id}/official-notice")
    assert failed.status_code == 503
    assert database.get_application(application_id)["status"] == "In Review"
    assert admissions.summary(application_id, next(u for u in database.users()
        if u["id"] == users["administrator"]))["notice"]["state"] == "failed"

    monkeypatch.setattr(mailer, "send_email", original_send)
    retry = client.post(f"/api/admissions/{application_id}/official-notice")
    assert retry.status_code == 200
    assert retry.json()["application_status"] == "Accepted"


def test_admin_no_final_recommendation_and_invalid_transcripts(environment):
    client, identity, users, application_id, _ = environment
    assert client.post(f"/api/admissions/{application_id}/official-notice").status_code == 409

    deliver_advisor_recommendation(client, identity, users, application_id, "Defer")
    assert client.post(f"/api/admissions/{application_id}/official-notice").status_code == 409

    from backend.service import graduate_college
    with database.connect() as db:
        db.execute("UPDATE graduate_college_decisions SET decision='Recommend' WHERE application_id=?", (application_id,))
    assert client.post(f"/api/admissions/{application_id}/official-notice").status_code == 200

    invalid = client.post(
        f"/api/admissions/{application_id}/official-transcript",
        files={"official_transcript": ("wrong.pdf", b"Not a PDF", "application/pdf")},
        data={"verified": "true"},
    )
    assert invalid.status_code == 422
    not_verified = client.post(
        f"/api/admissions/{application_id}/official-transcript",
        files={"official_transcript": ("yes.pdf", b"%PDF-1.4", "application/pdf")},
        data={"verified": "false"},
    )
    assert not_verified.status_code == 422


def test_conops_requires_complete_education_history_before_student_record(environment):
    client, identity, users, application_id, _ = environment
    deliver_advisor_recommendation(client, identity, users, application_id, "Recommend")
    assert client.post(f"/api/admissions/{application_id}/official-notice").status_code == 200
    application = database.get_application(application_id)
    application["fields"].pop("degree_start_date")
    database.save_application(application, application_id)

    pdf_bytes = b"%PDF-1.4\\n1 0 obj <<>> endobj\\n%%EOF"
    assert client.post(
        f"/api/admissions/{application_id}/official-transcript",
        files={"official_transcript": ("verified.pdf", pdf_bytes, "application/pdf")},
        data={"verified": "true"},
    ).status_code == 200
    response = client.post(
        f"/api/admissions/{application_id}/student-record",
        json={"tuition_classification": "resident"},
    )
    assert response.status_code == 422
    assert "education_history.degree_start_date" in response.json()["detail"]
    assert client.get(f"/api/admissions/{application_id}/student-record").status_code == 404


def test_administrator_page_renders_live_conops_workflow(environment):
    client, identity, users, application_id, _ = environment
    page = client.get("/administrator/admissions")
    assert page.status_code == 200
    assert "Avery Bennett" in page.text
    assert "No applications exist" not in page.text

    chosen = client.get(f"/administrator/admissions?application={application_id}")
    assert chosen.status_code == 200
    assert "Admissions Processing" in chosen.text
    assert "Graduate College notified" in chosen.text
    assert "Issue Official Admission Decision" in chosen.text

    deliver_advisor_recommendation(client, identity, users, application_id, "Recommend")
    ready = client.get(f"/administrator/admissions?application={application_id}")
    assert "Send official decision email" in ready.text
    assert "Create Student Record" not in ready.text

    assert client.post(f"/api/admissions/{application_id}/official-notice").status_code == 200
    accepted = client.get(f"/administrator/admissions?application={application_id}")
    assert "Open printable decision letter" in accepted.text
    assert "Create Student Record" in accepted.text
    assert "Save verified transcript" in accepted.text
