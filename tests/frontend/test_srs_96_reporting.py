"""SRS 9.6 reporting acceptance tests with isolated SQLite data."""
import csv
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.clients import database
from backend.service import accounts, graduate_college
from frontend.routes import reports


@pytest.fixture
def reporting(tmp_path, monkeypatch):
    monkeypatch.setenv("GDAS_DB_PATH", str(tmp_path / "reports.sqlite3"))
    admin_id = database.save_user({
        "username": "alex", "email": "alex@example.test",
        "first_name": "Alex", "last_name": "Morgan",
        "user_type": "administrator", "assigned_program_ids": [],
    })
    program_id = database.save_program({
        "degree_name": "Software Engineering",
        "degree_level": "masters", "campus_offered": ["main", "online"],
        "terms_offered": ["Fall 2027"],
        "application_questions": [{"id": "custom_research", "text": "Research interests"}],
    })
    other_id = database.save_program({
        "degree_name": "Computer Science",
        "degree_level": "masters", "campus_offered": ["main"],
    })
    advisor_id = database.save_user({
        "username": "taylor", "email": "taylor@example.test",
        "first_name": "Taylor", "last_name": "Bennett",
        "user_type": "advisor", "assigned_program_ids": [program_id],
    })
    applicant_id = database.save_user({
        "username": "avery", "email": "avery@example.test",
        "first_name": "Avery", "last_name": "Bennett",
        "user_type": "applicant", "assigned_program_ids": [],
    })
    users = {user["id"]: user for user in database.users()}
    active = {"user": users[admin_id]}
    monkeypatch.setattr(accounts, "session_user", lambda token: active["user"])
    app = FastAPI()
    app.include_router(reports.router)
    return {
        "client": TestClient(app),
        "active": active,
        "admin": users[admin_id],
        "advisor": users[advisor_id],
        "applicant": users[applicant_id],
        "program": program_id,
        "other_program": other_id,
        "owner": applicant_id,
    }


def add_application(ctx, name, status, program=None, fields=None, **kwargs):
    program_id = program or ctx["program"]
    return database.save_application({
        "owner_id": ctx["owner"],
        "program_id": program_id,
        "applicant_name": name, "full_name": name,
        "degree_program": "Software Engineering" if program_id == ctx["program"] else "Computer Science",
        "email": "student@example.test",
        "campus": "main", "term": "Fall 2027", "status": status,
        "submission_date": "2026-11-18T14:00:00+00:00" if status != "In Process" else "",
        "fields": fields or {},
        **kwargs,
    })


def saved_decision(application_id, decision):
    with database.connect() as db:
        graduate_college.ensure_tables(db)
        db.execute(
            """INSERT INTO graduate_college_decisions
            (application_id, advisor_id, decision, rationale)
            VALUES (?, 1, ?, 'Reviewed')""",
            (application_id, decision),
        )


def read_csv(response):
    assert response.status_code == 200, response.text
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["cache-control"] == "no-store"
    assert "attachment;" in response.headers["content-disposition"]
    return list(csv.DictReader(io.StringIO(response.text)))


def test_srs_961_current_submitted_report_details_gui_and_csv(reporting):
    ctx = reporting
    add_application(ctx, "Draft Only", "In Process")
    add_application(ctx, "Maya Thompson", "Submitted", fields={
        "citizenship": "United States", "university_name": "Southwest University",
        "date_of_birth": "2000-09-02", "cumulative_gpa": "3.7",
        "reference_1_name": "Dr. Test", "sponsor_information": "Research mentor",
        "custom_research": "Autonomous controls",
    })
    add_application(ctx, "Liam Parker", "Accepted")
    add_application(ctx, "Sophia Martinez", "Denied")
    page = ctx["client"].get("/administrator/reports", params={
        "report_type": "current-submitted", "program_id": ctx["program"], "generate": "1",
    })
    assert page.status_code == 200, page.text
    assert "3 records found." in " ".join(page.text.split())
    assert "Draft Only" not in page.text
    assert "Maya Thompson" in page.text
    assert "Dr. Test" in page.text
    assert "Autonomous controls" in page.text
    assert page.headers["cache-control"] == "no-store"

    data = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "current-submitted", "program_id": ctx["program"],
    }))
    assert len(data) == 3
    assert data[0]["Full Name"] in {"Sophia Martinez", "Liam Parker", "Maya Thompson"}
    maya = next(row for row in data if row["Full Name"] == "Maya Thompson")
    assert maya["University Name"] == "Southwest University"
    assert maya["Citizenship"] == "United States"
    assert maya["Reference 1 Name"] == "Dr. Test"
    assert "Research interests: Autonomous controls" in maya["Program-Specific Answers"]
    assert maya["Application Submission Date"].startswith("2026-11-18")


def test_srs_962_tailored_filters_and_selected_csv_columns(reporting):
    ctx = reporting
    add_application(ctx, "Maya Thompson", "In Review", fields={
        "citizenship": "United States", "ethnicity": "Hispanic",
        "sponsor_information": "Solar Energy Lab", "reference_1_name": "Dr. Vega",
    })
    add_application(ctx, "Avery Bennett", "In Review", fields={
        "citizenship": "Canada", "ethnicity": "Asian",
    })
    params = [
        ("report_type", "tailored"), ("program_id", str(ctx["program"])),
        ("citizenship", "united states"), ("sponsor_information", "solar"),
        ("fields", "full_name"), ("fields", "ethnicity"),
        ("fields", "reference_1_name"), ("fields", "citizenship"),
    ]
    page = ctx["client"].get("/administrator/reports", params=params + [("generate", "1")])
    assert page.status_code == 200, page.text
    assert "1 record found." in " ".join(page.text.split())
    assert "Maya Thompson" in page.text
    assert "Avery Bennett" not in page.text
    assert "Fields to Include" in page.text

    data = read_csv(ctx["client"].get("/administrator/reports.csv", params=params))
    assert data == [{
        "Full Name": "Maya Thompson",
        "Ethnicity": "Hispanic",
        "Reference 1 Name": "Dr. Vega",
        "Citizenship": "United States",
    }]


def test_srs_963_964_decision_reports_and_filters(reporting):
    ctx = reporting
    rec = add_application(ctx, "Recommended Applicant", "In Review")
    saved_decision(rec, "Recommend")
    add_application(ctx, "Matriculating Applicant", "Intent to Matriculate")
    add_application(ctx, "Accepted Applicant", "Accepted")
    add_application(ctx, "Denied Applicant", "Denied")
    deferred = add_application(ctx, "Deferred Applicant", "In Review")
    saved_decision(deferred, "Defer")
    add_application(ctx, "Unreviewed Applicant", "Submitted")

    accepted = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "accepted-approved",
    }))
    assert {row["Full Name"] for row in accepted} == {
        "Recommended Applicant", "Matriculating Applicant", "Accepted Applicant",
    }
    intended = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "accepted-approved", "decision": "Intent to Matriculate",
    }))
    assert [row["Full Name"] for row in intended] == ["Matriculating Applicant"]
    denied = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "denied-deferred",
    }))
    assert {row["Full Name"] for row in denied} == {
        "Denied Applicant", "Deferred Applicant",
    }


def test_srs_965_pending_review_report(reporting):
    ctx = reporting
    add_application(ctx, "Draft Applicant", "In Process")
    add_application(ctx, "Submitted Applicant", "Submitted")
    add_application(ctx, "Reviewing Applicant", "In Review")
    add_application(ctx, "Denied Applicant", "Denied")
    rows = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "pending-review", "status": "In Review",
    }))
    assert [row["Full Name"] for row in rows] == ["Reviewing Applicant"]
    all_rows = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "pending-review",
    }))
    assert {row["Full Name"] for row in all_rows} == {
        "Draft Applicant", "Submitted Applicant", "Reviewing Applicant",
    }


def test_srs_966_graphs_use_stored_gender_degree_and_ua_history(reporting):
    ctx = reporting
    add_application(ctx, "Avery Bennett", "Submitted", fields={
        "gender": "Female", "ethnicity": "Hispanic",
        "university_name": "University of Arizona", "degree_type": "Bachelors",
    })
    add_application(ctx, "Liam Parker", "In Review", fields={
        "gender": "Male", "ethnicity": "Hispanic",
        "university_name": "Northern Arizona University", "degree_type": "Bachelors",
    })
    add_application(ctx, "Maya Thompson", "Submitted")
    for key in ("degree_program", "ethnicity", "legal_residence_country",
                "gender", "campus", "degree_type", "ua_degree", "term",
                "application_status"):
        page = ctx["client"].get("/administrator/reports", params={
            "report_type": "graphical", "graph_type": key, "generate": "1",
        })
        assert page.status_code == 200, (key, page.text)
        assert "3 records found." in " ".join(page.text.split())
        assert "report-chart-bar" in page.text
    ua_page = ctx["client"].get("/administrator/reports", params={
        "report_type": "graphical", "graph_type": "ua_degree", "generate": "1",
    })
    assert "Previous Degree from University of Arizona" in ua_page.text
    assert "Not provided" in ua_page.text


def test_srs_96_advisor_program_scope_and_private_data_security(reporting):
    ctx = reporting
    add_application(ctx, "Allowed Applicant", "Submitted")
    add_application(ctx, "Other Program Applicant", "Submitted", program=ctx["other_program"])
    ctx["active"]["user"] = ctx["advisor"]
    page = ctx["client"].get("/advisor/reports", params={
        "report_type": "current-submitted", "generate": "1",
    })
    assert page.status_code == 200, page.text
    assert "Allowed Applicant" in page.text
    assert "Other Program Applicant" not in page.text
    csv_data = read_csv(ctx["client"].get("/advisor/reports.csv", params={
        "report_type": "current-submitted",
    }))
    assert [row["Full Name"] for row in csv_data] == ["Allowed Applicant"]
    other = read_csv(ctx["client"].get("/advisor/reports.csv", params={
        "report_type": "current-submitted", "program_id": ctx["other_program"],
    }))
    assert other == []
    assert ctx["client"].get("/administrator/reports").status_code == 403
    assert ctx["client"].get("/administrator/reports.csv").status_code == 403

    ctx["active"]["user"] = ctx["applicant"]
    assert ctx["client"].get("/advisor/reports").status_code == 403
    assert ctx["client"].get("/advisor/reports.csv").status_code == 403
    assert ctx["client"].get("/administrator/reports.csv").status_code == 403


def test_srs_96_csv_formula_protection_and_empty_fields(reporting):
    ctx = reporting
    add_application(ctx, "=DANGEROUS()", "Submitted", fields={
        "citizenship": "+HYPERLINK(1)", "date_of_birth": "2001-01-01",
    })
    rows = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "tailored",
        "fields": ["full_name", "citizenship", "official_transcripts"],
    }))
    assert rows == [{
        "Full Name": "'=DANGEROUS()",
        "Citizenship": "'+HYPERLINK(1)",
        "Official Transcripts": "",
    }]


def test_srs_962_custom_question_filter_and_srs_966_chart_csv(reporting):
    ctx = reporting
    add_application(ctx, "Avery Bennett", "Submitted", fields={
        "ethnicity": "Hispanic", "custom_research": "Solar energy controls",
    })
    add_application(ctx, "Maya Thompson", "Submitted", fields={
        "ethnicity": "Hispanic", "custom_research": "Embedded security",
    })
    add_application(ctx, "Liam Parker", "Submitted", fields={
        "ethnicity": "Asian",
    })

    result = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "tailored",
        "program_questions": "solar energy",
        "fields": ["full_name", "program_questions"],
    }))
    assert len(result) == 1
    assert result[0]["Full Name"] == "Avery Bennett"
    assert "Research interests: Solar energy controls" in result[0]["Program-Specific Answers"]

    chart = read_csv(ctx["client"].get("/administrator/reports.csv", params={
        "report_type": "graphical", "graph_type": "ethnicity",
    }))
    assert chart == [
        {"Category": "Hispanic", "Application Count": "2"},
        {"Category": "Asian", "Application Count": "1"},
    ]
