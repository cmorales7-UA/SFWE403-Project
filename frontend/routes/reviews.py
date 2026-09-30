from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# Mock review data
MOCK_ADMIN_APPLICATIONS = [
    {
        "id": 101,
        "applicant_name": "Chris Morales",
        "degree_program": "Software Engineering MS",
        "campus": "Main",
        "term": "Fall 2026",
        "status": "In Review",
        "review_comments": "",
        "recommendation": "",
    },
    {
        "id": 102,
        "applicant_name": "Emily Rodriguez",
        "degree_program": "Computer Science MS",
        "campus": "Main",
        "term": "Fall 2026",
        "status": "Submitted",
        "review_comments": "Strong academic background and relevant experience.",
        "recommendation": "recommend",
    },
    {
        "id": 103,
        "applicant_name": "Daniel Kim",
        "degree_program": "Systems Engineering MS",
        "campus": "Online",
        "term": "Spring 2027",
        "status": "In Review",
        "review_comments": "Additional review of prerequisite coursework is needed.",
        "recommendation": "defer",
    },
    {
        "id": 104,
        "applicant_name": "Maya Thompson",
        "degree_program": "Software Engineering MS",
        "campus": "Main",
        "term": "Spring 2027",
        "status": "Submitted",
        "review_comments": "",
        "recommendation": "",
    },
]


MOCK_ADVISOR_APPLICATIONS = [
    application
    for application in MOCK_ADMIN_APPLICATIONS
    if application["degree_program"] == "Software Engineering MS"
]


MOCK_REVIEWER_APPLICATIONS = [
    MOCK_ADMIN_APPLICATIONS[0],
    MOCK_ADMIN_APPLICATIONS[3],
]


def get_selected_application(applications, application_id):

    if not application_id:
        return None

    for application in applications:

        if str(application["id"]) == application_id:
            return application

    return None


# Reviewer application review
@router.get(
    "/reviewer/applications",
    response_class=HTMLResponse,
    name="reviewer_applications",
)
async def reviewer_applications(request: Request):

    application_id = request.query_params.get("application")

    selected_application = get_selected_application(
        MOCK_REVIEWER_APPLICATIONS,
        application_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="reviewer/review_applications.html",
        context={
            "applications": MOCK_REVIEWER_APPLICATIONS,
            "selected_application": selected_application,
        },
    )


# Advisor application review
@router.get(
    "/advisor/application-review",
    response_class=HTMLResponse,
    name="advisor_application_review",
)
async def advisor_application_review(request: Request):

    application_id = request.query_params.get("application")

    selected_application = get_selected_application(
        MOCK_ADVISOR_APPLICATIONS,
        application_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="advisor/application_review.html",
        context={
            "applications": MOCK_ADVISOR_APPLICATIONS,
            "selected_application": selected_application,
        },
    )


# Administrator application review
@router.get(
    "/administrator/application-review",
    response_class=HTMLResponse,
    name="administrator_application_review",
)
async def administrator_application_review(request: Request):

    application_id = request.query_params.get("application")

    selected_application = get_selected_application(
        MOCK_ADMIN_APPLICATIONS,
        application_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="administrator/application_review.html",
        context={
            "applications": MOCK_ADMIN_APPLICATIONS,
            "selected_application": selected_application,
        },
    )