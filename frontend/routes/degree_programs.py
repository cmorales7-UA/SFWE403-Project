from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# This router handles graduate degree program management pages.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# This route displays the Create Degree Program GUI for administrators.
@router.get(
    "/administrator/create-degree-program",
    response_class=HTMLResponse,
    name="administrator_create_degree_program",
)
async def administrator_create_degree_program(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="administrator/create_degree_program.html",
    )


# This route displays the Create Degree Program GUI for degree advisors.
@router.get(
    "/advisor/create-degree-program",
    response_class=HTMLResponse,
    name="advisor_create_degree_program",
)
async def advisor_create_degree_program(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="advisor/create_degree_program.html",
    )

# This route displays the Modify Degree Program GUI for administrators.
@router.get(
    "/administrator/modify-degree-program",
    response_class=HTMLResponse,
    name="administrator_modify_degree_program",
)
async def administrator_modify_degree_program(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="administrator/modify_degree_program.html",
        context={
            "degree_programs": [],
            "selected_degree": None,
        },
    )


# This route displays the Modify Degree Program GUI for degree advisors.
@router.get(
    "/advisor/modify-degree-program",
    response_class=HTMLResponse,
    name="advisor_modify_degree_program",
)
async def advisor_modify_degree_program(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="advisor/modify_degree_program.html",
        context={
            "degree_programs": [],
            "selected_degree": None,
        },
    )