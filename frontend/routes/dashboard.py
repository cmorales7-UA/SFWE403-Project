
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.clients import database
from backend.service import accounts, applications, graduate_college


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
    # Require an authenticated administrator, not just an authorized page URL.
    try:
        user = accounts.session_user(
            request.cookies.get("gdas_session", "")
        )
    except HTTPException as error:
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

    accounts.require_role(user, {"administrator"})

    # Read persisted data on every request. Do not use demo fixtures or
    # hardcoded counts: this is the same service used by application management.
    saved_applications = applications.list_applications(user)
    saved_programs = database.programs()

    summary = {
        "applications": len(saved_applications),
        # "Pending" means submitted or awaiting requested information.
        "pending": sum(
            item.get("status") in {"Submitted", "Needs Information"}
            for item in saved_applications
        ),
        "in_review": sum(
            item.get("status") == "In Review"
            for item in saved_applications
        ),
        "degree_programs": len(saved_programs),
    }

    # Distinguish formal outcomes from graduate-program recommendations.
    # Both come from persisted records; a missing decision is not mocked.
    application_rows = []
    for application in saved_applications:
        row = dict(application)
        if row.get("status") in {"Accepted", "Denied"}:
            row["decision_display"] = row["status"]
        else:
            program_decision = graduate_college.get_saved_decision(
                row["id"]
            )
            row["decision_display"] = (
                f"Program: {program_decision['decision']}"
                if program_decision
                else "Not decided"
            )
        application_rows.append(row)

    return templates.TemplateResponse(
        request=request,
        name="administrator/dashboard.html",
        context={
            "summary": summary,
            "applications": application_rows,
        },
        # Prevent the browser from reusing an old dashboard after edits.
        headers={"Cache-Control": "no-store"},
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
