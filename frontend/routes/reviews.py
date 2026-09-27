from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# Reviewer application review
@router.get(
    "/reviewer/applications",
    response_class=HTMLResponse,
    name="reviewer_applications",
)
async def reviewer_applications(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="reviewer/review_applications.html",
        context={
            "applications": [],
            "selected_application": None,
        },
    )


# Advisor application review
@router.get(
    "/advisor/application-review",
    response_class=HTMLResponse,
    name="advisor_application_review",
)
async def advisor_application_review(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="advisor/application_review.html",
        context={
            "applications": [],
            "selected_application": None,
        },
    )


# Administrator application review
@router.get(
    "/administrator/application-review",
    response_class=HTMLResponse,
    name="administrator_application_review",
)
async def administrator_application_review(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="administrator/application_review.html",
        context={
            "applications": [],
            "selected_application": None,
        },
    )