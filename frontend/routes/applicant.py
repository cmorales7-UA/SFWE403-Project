from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# This router handles pages used by student applicants.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# This route displays the Student Application GUI.
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


# This route displays the Modify Student Application GUI.
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