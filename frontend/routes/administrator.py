
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.service import accounts, applications
from frontend.routes.degrees import get_degree_program


# Administrator routes
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# Verify that the current user is an administrator.
def current_administrator(request: Request):

    try:
        user = accounts.session_user(
            request.cookies.get("gdas_session", "")
        )
    except HTTPException as error:
        if error.status_code == 401:
            return None
        raise

    if user["user_type"] != "administrator":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required"
        )

    return user


# Manage users
@router.get(
    "/administrator/manage-users",
    response_class=HTMLResponse,
    name="manage_users",
)
async def manage_users(request: Request):

    search_query = request.query_params.get("q", "")
    selected_user_type = request.query_params.get("user_type", "")

    return templates.TemplateResponse(
        request=request,
        name="administrator/manage_users.html",
        context={
            "users": [],
            "selected_user": None,
            "search_query": search_query,
            "selected_user_type": selected_user_type,
        },
    )


# View student applications
@router.get(
    "/administrator/student-applications",
    response_class=HTMLResponse,
    name="administrator_student_applications",
)
async def administrator_student_applications(request: Request):

    user = current_administrator(request)

    if user is None:
        return RedirectResponse("/login", status_code=303)

    # Retrieve all student applications from the backend.
    all_applications = applications.list_applications(user)

    # Retrieve existing search and filter selections.
    search_query = request.query_params.get("q", "").strip()
    selected_degree = request.query_params.get("degree", "")
    selected_term = request.query_params.get("term", "")
    selected_status = request.query_params.get("status", "")
    selected_application_id = request.query_params.get(
        "application", ""
    )

    # Filter applications based on search criteria.
    filtered_applications = []

    for application in all_applications:

        searchable = (
            f"{application['id']} "
            f"{application['full_name']} "
            f"{application['email']}"
        ).lower()

        if search_query.lower() not in searchable:
            continue

        if (
            selected_degree
            and application["degree_program"] != selected_degree
        ):
            continue

        if (
            selected_term
            and application["term"] != selected_term
        ):
            continue

        application_status = (
            application["status"].lower().replace(" ", "-")
        )

        if (
            selected_status
            and application_status != selected_status
        ):
            continue

        filtered_applications.append(application)

    # Retrieve the application selected by the administrator.
    selected_application = next(
        (
            application
            for application in all_applications
            if str(application["id"]) == selected_application_id
        ),
        None,
    )

    # Generate filter options from saved applications.
    degree_options = sorted({
        application["degree_program"]
        for application in all_applications
    })

    term_options = sorted({
        application["term"]
        for application in all_applications
    })

    return templates.TemplateResponse(
        request=request,
        name="administrator/student_applications.html",
        context={
            "applications": filtered_applications,
            "selected_application": selected_application,
            "search_query": search_query,
            "selected_degree": selected_degree,
            "selected_term": selected_term,
            "selected_status": selected_status,
            "selected_application_id": selected_application_id,
            "degree_options": degree_options,
            "term_options": term_options,
        },
    )


# Modify student application
@router.get(
    "/administrator/student-applications/{application_id}/modify",
    response_class=HTMLResponse,
    name="administrator_modify_student_application",
)
async def administrator_modify_student_application(
    request: Request,
    application_id: int,
):

    user = current_administrator(request)

    if user is None:
        return RedirectResponse("/login", status_code=303)

    # Retrieve the selected student application.
    application = applications.get_application(
        application_id,
        user
    )

    # Retrieve the degree program associated with the application.
    selected_degree = get_degree_program(
        application["program_id"]
    )

    return templates.TemplateResponse(
        request=request,
        name="administrator/modify_student_application.html",
        context={
            "application_id": application_id,
            "application": application,
            "selected_degree": selected_degree,
            "return_url": (
                "/administrator/student-applications"
                f"?application={application_id}"
            ),
        },
    )
