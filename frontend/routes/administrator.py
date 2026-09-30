from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# Administrator routes
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


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

    search_query = request.query_params.get("q", "")
    selected_degree = request.query_params.get("degree", "")
    selected_term = request.query_params.get("term", "")
    selected_status = request.query_params.get("status", "")
    selected_application_id = request.query_params.get("application", "")

    return templates.TemplateResponse(
        request=request,
        name="administrator/student_applications.html",
        context={
            "applications": [],
            "selected_application": None,
            "search_query": search_query,
            "selected_degree": selected_degree,
            "selected_term": selected_term,
            "selected_status": selected_status,
            "selected_application_id": selected_application_id,

            "degree_options": [],
            "term_options": [
                "Fall 2026",
                "Spring 2027",
                "Fall 2027",
                "Spring 2028",
                "Fall 2028"
            ],
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

    return templates.TemplateResponse(
        request=request,
        name="administrator/modify_student_application.html",
        context={
            "application_id": application_id,
            "application": None,
        },
    )