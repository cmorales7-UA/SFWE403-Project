
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.clients import database, reviewer_data
from backend.service import accounts, applications, graduate_college, review_committee


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


# Shared role check for dashboard pages.
def dashboard_actor(request: Request, role: str):
    try:
        actor = accounts.session_user(
            request.cookies.get("gdas_session", "")
        )
    except HTTPException as error:
        if error.status_code == 401:
            return None
        raise

    accounts.require_role(actor, {role})
    return actor


def dashboard_page(request, template, context):
    # Fetch all data on each request and prevent stale browser caching.
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=context,
        headers={"Cache-Control": "no-store"},
    )


def decision_display(application):
    if application.get("status") in {"Accepted", "Denied"}:
        return application["status"]

    decision = graduate_college.get_saved_decision(application["id"])
    return (
        f"Program: {decision['decision']}" if decision else "Not decided"
    )


# Advisor Dashboard
@router.get(
    "/advisor",
    response_class=HTMLResponse,
    name="advisor_dashboard",
)
async def advisor_dashboard(request: Request):
    actor = dashboard_actor(request, "advisor")
    if actor is None:
        return RedirectResponse("/login", status_code=303)

    # Application service only returns programs assigned to this advisor.
    visible_applications = applications.list_applications(actor)
    allowed_program_ids = set(actor.get("assigned_program_ids") or [])
    assigned_programs = [
        program
        for program in database.programs()
        if program["id"] in allowed_program_ids
    ]

    # A preliminary review is completed only when it was actually saved.
    # An in-review status by itself is not evidence of a saved review.
    pending = sum(
        application.get("status") in {"Submitted", "Needs Information"}
        and not (application.get("review") or {}).get("reviewed_at")
        for application in visible_applications
    )
    completed = sum(
        bool((application.get("review") or {}).get("reviewed_at"))
        for application in visible_applications
    )

    rows = [
        dict(application, decision_display=decision_display(application))
        for application in visible_applications
    ]

    return dashboard_page(
        request,
        "advisor/dashboard.html",
        {
            "summary": {
                "applications": len(rows),
                "reviews_pending": pending,
                "reviews_completed": completed,
                "degree_programs": len(assigned_programs),
            },
            "applications": rows,
        },
    )


# Reviewer Dashboard
@router.get(
    "/reviewer",
    response_class=HTMLResponse,
    name="reviewer_dashboard",
)
async def reviewer_dashboard(request: Request):
    actor = dashboard_actor(request, "reviewer")
    if actor is None:
        return RedirectResponse("/login", status_code=303)

    # Use the assignment service and exactly the permissions enforced by
    # the reviewer recommendation endpoint.
    allowed_program_ids = set(actor.get("assigned_program_ids") or [])
    rows = []
    for assignment in review_committee.list_assignments(actor):
        if assignment["program_id"] not in allowed_program_ids:
            continue

        recommendation = reviewer_data.get_recommendation(
            assignment["application_id"], actor["id"]
        )
        choice = (recommendation or {}).get("recommendation", "")
        completed = choice in {"recommend", "deny", "defer"}
        status = assignment["application_status"]

        rows.append({
            **assignment,
            "recommendation_display": choice.title() if completed else "Not entered",
            "review_completed": completed,
            "is_reviewable": status == "In Review",
        })

    completed = sum(row["review_completed"] for row in rows)
    return dashboard_page(
        request,
        "reviewer/dashboard.html",
        {
            "summary": {
                "assigned": len(rows),
                "pending": sum(
                    not row["review_completed"] and row["is_reviewable"]
                    for row in rows
                ),
                "completed": completed,
                "recommendations": completed,
            },
            "assignments": rows,
        },
    )


# Reference Dashboard
@router.get(
    "/reference",
    response_class=HTMLResponse,
    name="reference_dashboard",
)
async def reference_dashboard(request: Request):
    actor = dashboard_actor(request, "reference")
    if actor is None:
        return RedirectResponse("/login", status_code=303)

    # Reference requests belong to the recipient email address. Never
    # expose other recipients' requests and never infer a letter was sent.
    with database.connect() as connection:
        records = [
            dict(record)
            for record in connection.execute(
                """
                SELECT application_id, recipient_name, created_at
                FROM recommendation_requests
                WHERE LOWER(recipient_email) = LOWER(?)
                ORDER BY created_at DESC, id DESC
                """,
                (actor.get("email") or "",),
            )
        ]

    requests = []
    for record in records:
        application = database.get_application(record["application_id"])
        if application is None:
            continue
        requests.append({
            "applicant_name": application.get("applicant_name", "Applicant"),
            "degree_program": application.get("degree_program", ""),
            "status": "Requested",
        })

    # Letter submissions are not persisted in UA-GDAS yet. Show only
    # verifiable metrics rather than inventing completed/pending counts.
    return dashboard_page(
        request,
        "reference/dashboard.html",
        {
            "summary": {
                "requests": len(requests),
                "applicants": len({row["applicant_name"] for row in requests}),
                "programs": len({row["degree_program"] for row in requests}),
            },
            "requests": requests,
        },
    )


# IT Support Dashboard
@router.get(
    "/it-support",
    response_class=HTMLResponse,
    name="it_support_dashboard",
)
async def it_support_dashboard(request: Request):
    actor = dashboard_actor(request, "it_support")
    if actor is None:
        return RedirectResponse("/login", status_code=303)

    users = accounts.list_users(actor)
    applicants = sum(user.get("user_type") == "applicant" for user in users)
    return dashboard_page(
        request,
        "it_support/dashboard.html",
        {
            "summary": {
                "accounts": len(users),
                "applicants": applicants,
                "staff": len(users) - applicants,
            },
            "users": users,
        },
    )


# IT Support account management remains a separate frontend integration
# task; dashboard counts above already reflect real persisted accounts.
@router.get(
    "/it-support/manage-users",
    response_class=HTMLResponse,
    name="it_support_manage_users",
)
async def it_support_manage_users(request: Request):
    actor = dashboard_actor(request, "it_support")
    if actor is None:
        return RedirectResponse("/login", status_code=303)

    search_query = request.query_params.get("q", "").strip()
    selected_user_type = request.query_params.get("user_type", "").strip()
    selected_id = request.query_params.get("user", "").strip()

    matching = []
    all_users = accounts.list_users(actor)
    for item in all_users:
        searchable = " ".join(str(item.get(key) or "") for key in (
            "first_name", "last_name", "username", "email", "net_id"
        )).casefold()
        if search_query and search_query.casefold() not in searchable:
            continue
        if selected_user_type and item.get("user_type") != selected_user_type:
            continue
        matching.append(item)

    selected_user = next(
        (item for item in all_users if str(item["id"]) == selected_id),
        None,
    )
    return dashboard_page(
        request,
        "it_support/manage_users.html",
        {
            "users": matching,
            "selected_user": selected_user,
            "search_query": search_query,
            "selected_user_type": selected_user_type,
        },
    )
