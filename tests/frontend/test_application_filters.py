from fastapi import FastAPI
from fastapi.testclient import TestClient

from frontend.routes import application_filters
from tests.fixtures.application_filters import (
    TEST_FILTER_APPLICATIONS,
    TEST_FILTER_OPTIONS,
)


def create_test_client():
    app = FastAPI()
    app.include_router(application_filters.router)

    return TestClient(app)


def test_administrator_filter_page_loads(monkeypatch):
    monkeypatch.setattr(
        application_filters,
        "get_application_filter_options",
        lambda user_role: TEST_FILTER_OPTIONS,
    )

    monkeypatch.setattr(
        application_filters,
        "get_authorized_applications",
        lambda user_role, filters: TEST_FILTER_APPLICATIONS,
    )

    client = create_test_client()

    response = client.get(
        "/administrator/filter-applications"
    )

    assert response.status_code == 200

    html = response.text

    assert "Filter Applications" in html
    assert "Applicant Name" in html
    assert "Degree Program" in html
    assert "Term" in html
    assert "Status" in html
    assert "Applicant Gender" in html
    assert "Country of Legal Residence" in html
    assert "Campus" in html
    assert "Decision" in html


def test_required_status_and_decision_options(monkeypatch):
    monkeypatch.setattr(
        application_filters,
        "get_application_filter_options",
        lambda user_role: TEST_FILTER_OPTIONS,
    )

    monkeypatch.setattr(
        application_filters,
        "get_authorized_applications",
        lambda user_role, filters: [],
    )

    client = create_test_client()

    response = client.get(
        "/administrator/filter-applications"
    )

    assert response.status_code == 200

    html = response.text

    assert 'value="Pending"' in html
    assert 'value="Submitted"' in html
    assert 'value="In Review"' in html

    assert 'value="Recommend"' in html
    assert 'value="Deny"' in html
    assert 'value="Defer"' in html
    assert 'value="Intent to Matriculate"' in html


def test_multiple_filters_are_passed_together(monkeypatch):
    received = {}

    monkeypatch.setattr(
        application_filters,
        "get_application_filter_options",
        lambda user_role: TEST_FILTER_OPTIONS,
    )

    def fake_get_authorized_applications(
        user_role,
        filters,
    ):
        received["user_role"] = user_role
        received["filters"] = filters

        return []

    monkeypatch.setattr(
        application_filters,
        "get_authorized_applications",
        fake_get_authorized_applications,
    )

    client = create_test_client()

    response = client.get(
        "/administrator/filter-applications",
        params={
            "degree": "Software Engineering",
            "applicant_name": "Chris",
            "gender": "Male",
            "country": "United States",
            "campus": "Main",
            "term": "Fall 2026",
            "status": "In Review",
            "decision": "Recommend",
        },
    )

    assert response.status_code == 200

    assert received["user_role"] == "administrator"

    assert received["filters"] == {
        "degree": "Software Engineering",
        "applicant_name": "Chris",
        "gender": "Male",
        "country": "United States",
        "campus": "Main",
        "term": "Fall 2026",
        "status": "In Review",
        "decision": "Recommend",
    }


def test_selected_filters_remain_selected(monkeypatch):
    monkeypatch.setattr(
        application_filters,
        "get_application_filter_options",
        lambda user_role: TEST_FILTER_OPTIONS,
    )

    monkeypatch.setattr(
        application_filters,
        "get_authorized_applications",
        lambda user_role, filters: [],
    )

    client = create_test_client()

    response = client.get(
        "/administrator/filter-applications",
        params={
            "degree": "Software Engineering",
            "term": "Fall 2026",
            "status": "In Review",
            "campus": "Main",
            "decision": "Recommend",
        },
    )

    assert response.status_code == 200

    html = " ".join(response.text.split())

    assert (
        'value="Software Engineering" selected'
        in html
    )
    assert (
        'value="Fall 2026" selected'
        in html
    )
    assert (
        'value="In Review" selected'
        in html
    )
    assert (
        'value="Main" selected'
        in html
    )
    assert (
        'value="Recommend" selected'
        in html
    )

def test_no_filters_returns_authorized_listing(monkeypatch):
    monkeypatch.setattr(
        application_filters,
        "get_application_filter_options",
        lambda user_role: TEST_FILTER_OPTIONS,
    )

    monkeypatch.setattr(
        application_filters,
        "get_authorized_applications",
        lambda user_role, filters: TEST_FILTER_APPLICATIONS,
    )

    client = create_test_client()

    response = client.get(
        "/administrator/filter-applications"
    )

    assert response.status_code == 200

    html = " ".join(response.text.split())

    assert (
        "2 applications available to your account."
        in html
    )
    assert "Chris Morales" in html
    assert "Emily Rodriguez" in html


def test_advisor_filter_page_uses_advisor_role(
    monkeypatch,
):
    received = {}

    monkeypatch.setattr(
        application_filters,
        "get_application_filter_options",
        lambda user_role: TEST_FILTER_OPTIONS,
    )

    def fake_get_authorized_applications(
        user_role,
        filters,
    ):
        received["user_role"] = user_role

        return []

    monkeypatch.setattr(
        application_filters,
        "get_authorized_applications",
        fake_get_authorized_applications,
    )

    client = create_test_client()

    response = client.get(
        "/advisor/filter-applications"
    )

    assert response.status_code == 200
    assert received["user_role"] == "advisor"
    assert "Degree Advisor" in response.text