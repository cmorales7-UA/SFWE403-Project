
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.service import accounts, applications
from frontend.routes.degrees import get_degree_program


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# --------------------------------------------------
# Application Review Configuration
# --------------------------------------------------

# Applications must be submitted before review.
REVIEWABLE_STATUSES = {
    "Submitted",
    "Needs Information",
    "In Review",
}


# --------------------------------------------------
# Authentication and Role Verification
# --------------------------------------------------

def current_role(request: Request, required_role: str):

    try:
        user = accounts.session_user(
            request.cookies.get("gdas_session", "")
        )

    except HTTPException as error:
        if error.status_code == 401:
            return None
        raise

    if user["user_type"] != required_role:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this page"
        )

    return user


def current_advisor(request: Request):

    return current_role(request, "advisor")


# --------------------------------------------------
# Application Review Helpers
# --------------------------------------------------

def reviewable_applications(user):

    # Retrieve actual application records from SQLite.
    # The backend enforces application access permissions.
    authorized_applications = applications.list_applications(user)

    return [
        item
        for item in authorized_applications
        if item.get("status") in REVIEWABLE_STATUSES
    ]


def selected_review_application(application_id, user):

    if application_id is None:
        return None

    # Retrieve the application using the existing
    # SRS 9.4.1 authorization rules.
    application = applications.get_application(
        application_id,
        user
    )

    if application.get("status") not in REVIEWABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="This application is not available for review"
        )

    return application


# --------------------------------------------------
# Reviewer Application Review
# --------------------------------------------------

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
            status_code=303
        )

    # Reviewer application assignments are not yet
    # implemented in the backend.
    # Do not expose unassigned student applications.
    if application is not None:
        raise HTTPException(
            status_code=403,
            detail="No authorized application assignment is available"
        )

    return templates.TemplateResponse(
        request=request,
        name="reviewer/review_applications.html",
        context={
            "applications": [],
            "selected_application": None,
            "advisor_messages": [],
        },
    )


# --------------------------------------------------
# SRS 9.4.2 - Advisor Preliminary Review
# --------------------------------------------------

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
            status_code=303
        )

    # Retrieve submitted applications belonging
    # to the Advisor's assigned degree programs.
    assigned_applications = reviewable_applications(user)

    selected_application = selected_review_application(
        application,
        user
    )

    return templates.TemplateResponse(
        request=request,
        name="advisor/application_review.html",
        context={
            "applications": assigned_applications,
            "selected_application": selected_application,
        },
    )


# --------------------------------------------------
# Administrator Application Review
# --------------------------------------------------

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
            status_code=303
        )

    # Administrators can retrieve submitted
    # applications from all degree programs.
    available_applications = reviewable_applications(user)

    selected_application = selected_review_application(
        application,
        user
    )

    if selected_application is not None:

        # Make existing stored review comments available
        # to the Administrator's current review template.
        review = selected_application.get("review") or {}

        selected_application["review_comments"] = (
            review.get("review_comments", "")
        )

        selected_application["recommendation"] = (
            review.get("recommendation", "")
        )

    return templates.TemplateResponse(
        request=request,
        name="administrator/application_review.html",
        context={
            "applications": available_applications,
            "selected_application": selected_application,
        },
    )


# --------------------------------------------------
# SRS 9.4.1 - Advisor Application Management
# --------------------------------------------------

# View applications for assigned degree programs.
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
            status_code=303
        )

    # Retrieve only authorized applications.
    assigned_applications = applications.list_applications(user)

    return templates.TemplateResponse(
        request=request,
        name="advisor/manage_applications.html",
        context={
            "applications": assigned_applications,
        },
    )


# Modify an application for an assigned degree program.
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
            status_code=303
        )

    # Retrieve application and verify permissions.
    application = applications.get_application(
        application_id,
        user
    )

    # Retrieve the associated degree program.
    selected_degree = get_degree_program(
        application["program_id"]
    )

    return templates.TemplateResponse(
        request=request,
        name="advisor/modify_application.html",
        context={
            "application": application,
            "selected_degree": selected_degree,
            "return_url": "/advisor/applications",
        },
    )
