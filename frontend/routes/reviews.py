from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.service import (
    accounts,
    applications,
    programs,
    review_committee,
)
from frontend.routes.degrees import get_degree_program

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

REVIEWABLE_STATUSES = {
    "Submitted",
    "Needs Information",
    "In Review",
}


def current_role(request: Request, required_role: str):
    try:
        user = accounts.session_user(request.cookies.get("gdas_session", ""))
    except HTTPException as error:
        if error.status_code == 401:
            return None
        raise

    if user["user_type"] != required_role:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this page",
        )

    return user


def current_advisor(request: Request):
    return current_role(request, "advisor")


def reviewable_applications(user):
    authorized = applications.list_applications(user)

    return [item for item in authorized if item.get("status") in REVIEWABLE_STATUSES]


def selected_review_application(application_id, user):
    if application_id is None:
        return None

    application = applications.get_application(
        application_id,
        user,
    )

    if application.get("status") not in REVIEWABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="This application is not available for review",
        )

    return application


def reviewer_application_details(application):
    """Prepare stored form fields for the existing review page."""

    result = dict(application)
    fields = application.get("fields") or {}

    for key in (
        "citizenship",
        "legal_residence_country",
        "previous_ua_affiliation",
    ):
        result[key] = fields.get(key, "")

    if fields.get("university_name"):
        result["education_history"] = [
            {
                "degree_name": fields.get("education_degree_name", ""),
                "university_name": fields.get("university_name", ""),
                "degree_type": fields.get("degree_type", ""),
                "cumulative_gpa": fields.get("cumulative_gpa", ""),
                "total_credits": fields.get("total_credits", ""),
                "date_degree_received": fields.get("degree_received_date", ""),
            }
        ]
    else:
        result["education_history"] = []

    questions = (
        ("Sponsor Information", "sponsor_information"),
        ("TA or RA Experience", "ta_ra_experience"),
        ("Funding Information", "funding_information"),
    )

    result["supplemental_responses"] = [
        {
            "question": label,
            "answer": fields[key],
        }
        for label, key in questions
        if fields.get(key)
    ]

    return result


@router.get(
    "/reviewer/applications",
    response_class=HTMLResponse,
    name="reviewer_applications",
)
async def reviewer_applications(
    request: Request,
    application: int | None = None,
):
    user = current_role(request, "reviewer")

    if user is None:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    assigned_applications = review_committee.list_assignments(user)

    selected_application = None

    if application is not None:
        # The service checks the reviewer's actual assignment.
        record = review_committee.get_reviewer_application(
            application,
            user,
        )

        selected_application = reviewer_application_details(record)

    return templates.TemplateResponse(
        request=request,
        name="reviewer/review_applications.html",
        context={
            "applications": assigned_applications,
            "selected_application": selected_application,
            "advisor_messages": [],
        },
    )


@router.get(
    "/advisor/application-review",
    response_class=HTMLResponse,
    name="advisor_application_review",
)
async def advisor_application_review(
    request: Request,
    application: int | None = None,
):
    user = current_advisor(request)

    if user is None:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    assigned_applications = reviewable_applications(user)

    selected_application = selected_review_application(
        application,
        user,
    )

    return templates.TemplateResponse(
        request=request,
        name="advisor/application_review.html",
        context={
            "applications": assigned_applications,
            "selected_application": selected_application,
        },
    )


@router.get(
    "/advisor/review-committee",
    response_class=HTMLResponse,
    name="advisor_review_committee",
)
async def advisor_review_committee(request: Request):
    user = current_advisor(request)

    if user is None:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    assigned_program_ids = set(user.get("assigned_program_ids") or [])

    available_programs = [
        program
        for program in programs.list_programs(user)
        if program["id"] in assigned_program_ids
    ]

    ready_applications = [
        application
        for application in applications.list_applications(user)
        if application.get("status") == "In Review"
    ]

    reviewers = review_committee.list_reviewers(user)
    assignments = review_committee.list_assignments(user)

    return templates.TemplateResponse(
        request=request,
        name="advisor/review_committee.html",
        context={
            "programs": available_programs,
            "applications": ready_applications,
            "reviewers": reviewers,
            "assignments": assignments,
        },
    )


@router.get(
    "/administrator/application-review",
    response_class=HTMLResponse,
    name="administrator_application_review",
)
async def administrator_application_review(
    request: Request,
    application: int | None = None,
):
    user = current_role(request, "administrator")

    if user is None:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    available_applications = reviewable_applications(user)

    selected_application = selected_review_application(
        application,
        user,
    )

    if selected_application is not None:
        review = selected_application.get("review") or {}

        selected_application["review_comments"] = review.get("review_comments", "")

        selected_application["recommendation"] = review.get("recommendation", "")

    return templates.TemplateResponse(
        request=request,
        name="administrator/application_review.html",
        context={
            "applications": available_applications,
            "selected_application": selected_application,
        },
    )


@router.get(
    "/advisor/applications",
    response_class=HTMLResponse,
    name="advisor_manage_applications",
)
async def advisor_manage_applications(request: Request):
    user = current_advisor(request)

    if user is None:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    assigned_applications = applications.list_applications(user)

    return templates.TemplateResponse(
        request=request,
        name="advisor/manage_applications.html",
        context={
            "applications": assigned_applications,
        },
    )


@router.get(
    "/advisor/applications/{application_id}/modify",
    response_class=HTMLResponse,
    name="advisor_modify_application",
)
async def advisor_modify_application(
    request: Request,
    application_id: int,
):
    user = current_advisor(request)

    if user is None:
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    application = applications.get_application(
        application_id,
        user,
    )

    selected_degree = get_degree_program(application["program_id"])

    return templates.TemplateResponse(
        request=request,
        name="advisor/modify_application.html",
        context={
            "application": application,
            "selected_degree": selected_degree,
            "return_url": "/advisor/applications",
        },
    )


# SRS 9.4.5: Graduate College Decisions


@router.get(
    "/advisor/graduate-college",
    response_class=HTMLResponse,
    name="advisor_graduate_college",
)
async def advisor_graduate_college(request: Request):
    user = current_advisor(request)

    if user is None:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="advisor/graduate_college.html",
        context={},
    )


# SRS 9.4.6: Review Committee monitoring


@router.get(
    "/advisor/review-status",
    response_class=HTMLResponse,
    name="advisor_review_status",
)
async def advisor_review_status(request: Request):
    user = current_role(request, "advisor")

    if user is None:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="reviews/review_status.html",
        context={"user_role": "advisor"},
    )


@router.get(
    "/administrator/review-status",
    response_class=HTMLResponse,
    name="administrator_review_status",
)
async def administrator_review_status(request: Request):
    user = current_role(request, "administrator")

    if user is None:
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="reviews/review_status.html",
        context={"user_role": "administrator"},
    )
