from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# This router handles the different user dashboard pages.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


@router.get(
    "/applicant",
    response_class=HTMLResponse,
    name="applicant_dashboard",
)
async def applicant_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="applicant/dashboard.html",
    )


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