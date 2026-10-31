
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.service import accounts, applications


# This router handles the different user dashboard pages.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# Applicant Dashboard
@router.get(
    "/applicant",
    response_class=HTMLResponse,
    name="applicant_dashboard",
)
async def applicant_dashboard(request: Request):

    # Verify the user is logged in.
    try:
        user = accounts.session_user(
            request.cookies.get("gdas_session", "")
        )
    except HTTPException as error:
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

    # Only applicants can access this dashboard.
    if user["user_type"] != "applicant":
        raise HTTPException(
            status_code=403,
            detail="Applicant access required"
        )

    # Retrieve applications belonging to the logged-in applicant.
    student_applications = applications.list_applications(user)

    # Use the newest application for the dashboard summary.
    current_application = (
        student_applications[0]
        if student_applications
        else None
    )

    return templates.TemplateResponse(
        request=request,
        name="applicant/dashboard.html",
        context={
            "applications": student_applications,
            "current_application": current_application,
        },
    )


# Administrator Dashboard
@router.get(
    "/administrator",
    response_class=HTMLResponse,
    name="administrator_dashboard",
)
async def administrator_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="administrator/dashboard.html",
    )


# Advisor Dashboard
@router.get(
    "/advisor",
    response_class=HTMLResponse,
    name="advisor_dashboard",
)
async def advisor_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="advisor/dashboard.html",
    )


# Reviewer Dashboard
@router.get(
    "/reviewer",
    response_class=HTMLResponse,
    name="reviewer_dashboard",
)
async def reviewer_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="reviewer/dashboard.html",
    )


# Reference Dashboard
@router.get(
    "/reference",
    response_class=HTMLResponse,
    name="reference_dashboard",
)
async def reference_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="reference/dashboard.html",
    )


# IT Support Dashboard
@router.get(
    "/it-support",
    response_class=HTMLResponse,
    name="it_support_dashboard",
)
async def it_support_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="it_support/dashboard.html",
    )


@router.get(
    "/it-support/manage-users",
    response_class=HTMLResponse,
    name="it_support_manage_users",
)
async def it_support_manage_users(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="it_support/manage_users.html",
        context={
            "users": [],
            "selected_user": None,
            "search_query": "",
            "selected_user_type": "",
        },
    )
