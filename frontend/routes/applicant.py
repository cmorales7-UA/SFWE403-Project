from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# This router handles pages used by student applicants.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# This route displays the applicant's existing applications.
@router.get(
    "/applicant/applications",
    response_class=HTMLResponse,
    name="my_applications",
)
async def my_applications(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="applicant/my_applications.html",
        context={
            # Application data will be supplied by the backend.
            "applications": [],
        },
    )


# This route displays the form for starting a new application.
@router.get(
    "/applicant/application",
    response_class=HTMLResponse,
    name="student_application",
)
async def student_application(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="applicant/student_application.html",
    )


# This route displays an existing application for modification.
@router.get(
    "/applicant/modify-application",
    response_class=HTMLResponse,
    name="modify_application",
)
async def modify_application(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="applicant/modify_application.html",
    )