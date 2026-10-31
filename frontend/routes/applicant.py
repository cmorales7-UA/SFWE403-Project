from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from frontend.routes.degrees import get_degree_program
from backend.service import accounts, applications


# This router handles pages used by student applicants.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


def current_applicant(request: Request):
    """Enforce the authenticated applicant role for private application pages."""
    try:
        user = accounts.session_user(request.cookies.get("gdas_session", ""))
    except HTTPException as exc:
        if exc.status_code == 401:
            return None
        raise
    if user["user_type"] != "applicant":
        raise HTTPException(403, "Applicant access required")
    return user


# This route displays the applicant's existing applications.
@router.get(
    "/applicant/applications",
    response_class=HTMLResponse,
    name="my_applications",
)
async def my_applications(request: Request):
    user = current_applicant(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="applicant/my_applications.html",
        context={
            "applications": applications.list_applications(user),
        },
    )


# This route displays the form for starting a new application.
@router.get(
    "/applicant/application",
    response_class=HTMLResponse,
    name="student_application",
)
async def student_application(
    request: Request,
    degree_id: int | None = None,
):
    user = current_applicant(request)

    if user is None:
        return RedirectResponse("/login", status_code=303)

    selected_degree = None

    if degree_id is not None:
        selected_degree = get_degree_program(degree_id)

    return templates.TemplateResponse(
        request=request,
        name="applicant/student_application.html",
        context={
            "selected_degree": selected_degree,
        },
    )


# This route displays an existing application for modification.
@router.get(
    "/applicant/modify-application",
    response_class=HTMLResponse,
    name="modify_application",
)
async def modify_application(request: Request, application_id: int):
    user = current_applicant(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    application = applications.get_application(application_id, user)
    return templates.TemplateResponse(
        request=request,
        name="applicant/modify_application.html",
        context={
            "application": application,
            "selected_degree": get_degree_program(application["program_id"]),
        },
    )
