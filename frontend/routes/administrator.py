
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from urllib.parse import urlencode

from backend.clients import database
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


# Manage users: query the same account service used by /api/users.
@router.get(
    "/administrator/manage-users",
    response_class=HTMLResponse,
    name="manage_users",
)
async def manage_users(request: Request):
    actor = current_administrator(request)
    if actor is None:
        return RedirectResponse("/login", status_code=303)

    query = request.query_params.get("q", "").strip()
    selected_user_type = request.query_params.get("user_type", "").strip()
    selected_id = request.query_params.get("user", "").strip()
    raw_page = request.query_params.get("page", "1")
    page = max(int(raw_page), 1) if raw_page.isdigit() else 1

    # Public-safe account records, never stored password/security hashes.
    all_users = accounts.list_users(actor)
    matching = []
    for account in all_users:
        if selected_user_type and account.get("user_type") != selected_user_type:
            continue

        searchable = " ".join(str(account.get(field) or "") for field in (
            "first_name", "last_name", "username", "email", "net_id",
        )).casefold()
        if query and query.casefold() not in searchable:
            continue
        matching.append(account)

    matching.sort(key=lambda account: (
        str(account.get("last_name") or "").casefold(),
        str(account.get("first_name") or "").casefold(),
        account["id"],
    ))

    per_page = 12
    total_pages = max(1, (len(matching) + per_page - 1) // per_page)
    page = min(page, total_pages)
    users_page = matching[(page - 1) * per_page:page * per_page]

    # Selecting a user cannot bypass the role check above. A selection is
    # independent of the search filter so an edited role remains viewable.
    selected_user = next(
        (account for account in all_users if str(account["id"]) == selected_id),
        None,
    )
    base_query = urlencode({
        "q": query,
        "user_type": selected_user_type,
        "page": page,
    })

    def page_url(number):
        return "/administrator/manage-users?" + urlencode({
            "q": query,
            "user_type": selected_user_type,
            "page": number,
        })

    return templates.TemplateResponse(
        request=request,
        name="administrator/manage_users.html",
        context={
            "users": users_page,
            "selected_user": selected_user,
            "search_query": query,
            "selected_user_type": selected_user_type,
            "page": page,
            "total_pages": total_pages,
            "total_results": len(matching),
            "base_query": base_query,
            "previous_url": page_url(page - 1) if page > 1 else None,
            "next_url": page_url(page + 1) if page < total_pages else None,
            "programs": sorted(
                database.programs(),
                key=lambda program: program["degree_name"].casefold(),
            ),
            "save_success": (
                selected_user is not None
                and request.query_params.get("saved") == "1"
            ),
        },
        headers={"Cache-Control": "no-store"},
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
