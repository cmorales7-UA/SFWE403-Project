from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


TERM_OPTIONS = [
    "Fall 2026",
    "Spring 2027",
    "Fall 2027",
    "Spring 2028",
    "Fall 2028",
]


def get_filter_context(request: Request, user_role: str):

    filters = {
        "degree": request.query_params.get("degree", ""),
        "applicant_name": request.query_params.get("applicant_name", ""),
        "gender": request.query_params.get("gender", ""),
        "country": request.query_params.get("country", ""),
        "campus": request.query_params.get("campus", ""),
        "term": request.query_params.get("term", ""),
        "status": request.query_params.get("status", ""),
        "decision": request.query_params.get("decision", ""),
    }

    return {
        "user_role": user_role,
        "applications": [],
        "degree_options": [],
        "term_options": TERM_OPTIONS,
        "filters": filters,
        "has_filters": any(filters.values()),
    }


# Administrator application filters
@router.get(
    "/administrator/filter-applications",
    response_class=HTMLResponse,
    name="administrator_filter_applications",
)
async def administrator_filter_applications(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="applications/filter_applications.html",
        context=get_filter_context(
            request,
            "administrator",
        ),
    )


# Advisor application filters
@router.get(
    "/advisor/filter-applications",
    response_class=HTMLResponse,
    name="advisor_filter_applications",
)
async def advisor_filter_applications(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="applications/filter_applications.html",
        context=get_filter_context(
            request,
            "advisor",
        ),
    )