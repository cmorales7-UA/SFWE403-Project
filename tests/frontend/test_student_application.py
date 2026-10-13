from fastapi import FastAPI
from fastapi.testclient import TestClient

from frontend.routes import applicant, degrees
from tests.fixtures.degree_programs import TEST_DEGREE_PROGRAMS


def create_test_client():
    app = FastAPI()
    app.include_router(applicant.router)

    return TestClient(app)


def test_get_software_engineering_degree(monkeypatch):
    monkeypatch.setattr(
        degrees,
        "get_degree_programs",
        lambda: TEST_DEGREE_PROGRAMS,
    )

    selected_degree = degrees.get_degree_program(2)

    assert selected_degree is not None
    assert selected_degree["name"] == "Software Engineering"
    assert selected_degree["campus_offered"] == [
        "main",
        "online",
    ]
    assert selected_degree["terms_offered"] == [
        "Spring 2028",
        "Fall 2028",
    ]


def test_computer_science_only_has_fall_2027(monkeypatch):
    monkeypatch.setattr(
        degrees,
        "get_degree_programs",
        lambda: TEST_DEGREE_PROGRAMS,
    )

    selected_degree = degrees.get_degree_program(1)

    assert selected_degree is not None
    assert selected_degree["terms_offered"] == [
        "Fall 2027",
    ]


def test_unknown_degree_returns_none(monkeypatch):
    monkeypatch.setattr(
        degrees,
        "get_degree_programs",
        lambda: TEST_DEGREE_PROGRAMS,
    )

    selected_degree = degrees.get_degree_program(999)

    assert selected_degree is None


def test_software_engineering_application_page(monkeypatch):
    monkeypatch.setattr(
        degrees,
        "get_degree_programs",
        lambda: TEST_DEGREE_PROGRAMS,
    )

    client = create_test_client()

    response = client.get(
        "/applicant/application?degree_id=2"
    )

    assert response.status_code == 200

    html = response.text

    assert "Software Engineering" in html
    assert 'value="main"' in html
    assert 'value="online"' in html
    assert "Spring 2028" in html
    assert "Fall 2028" in html

    # Terms from another program should not appear.
    assert "Fall 2027" not in html


def test_computer_science_application_page(monkeypatch):
    monkeypatch.setattr(
        degrees,
        "get_degree_programs",
        lambda: TEST_DEGREE_PROGRAMS,
    )

    client = create_test_client()

    response = client.get(
        "/applicant/application?degree_id=1"
    )

    assert response.status_code == 200

    html = response.text

    assert "Computer Science" in html
    assert 'value="main"' in html
    assert 'value="online"' in html
    assert "Fall 2027" in html

    # Computer Science does not offer these terms.
    assert "Spring 2028" not in html
    assert "Fall 2028" not in html


def test_application_without_degree_selection(monkeypatch):
    monkeypatch.setattr(
        degrees,
        "get_degree_programs",
        lambda: TEST_DEGREE_PROGRAMS,
    )

    client = create_test_client()

    response = client.get(
        "/applicant/application"
    )

    assert response.status_code == 200
    assert (
        "Select a graduate degree program before starting an application."
        in response.text
    )
    assert "Browse Graduate Degrees" in response.text