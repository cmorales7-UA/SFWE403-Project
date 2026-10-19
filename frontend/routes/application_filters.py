from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


STATUS_OPTIONS = [
    "Pending",
    "Submitted",
    "In Review",
]

DECISION_OPTIONS = [
    "Recommend",
    "Deny",
    "Defer",
    "Intent to Matriculate",
]

CAMPUS_OPTIONS = [
    "Main",
    "Online",
    "Distance",
]

GENDER_OPTIONS = [
    "Male",
    "Female",
]


def get_application_filter_options(user_role: str):
    """
    Backend integration point.

    Degree and term options should come from the current
    graduate degree/application data.
    """

    return {
        "degree_options": [],
        "term_options": [],
    }


def get_authorized_applications(
    user_role: str,
    filters: dict,
):
    """
    Backend integration point.

    The backend should return only applications the current
    user is authorized to access.

    When multiple filters are supplied, the backend should
    combine them using AND conditions.

    When no filters are supplied, return the full authorized
    application listing for the current user.
    """

    return []


def get_filter_context(
    request: Request,
    user_role: str,
):

    filters = {
        "degree": request.query_params.get(
            "degree",
            "",
        ).strip(),
        "applicant_name": request.query_params.get(
            "applicant_name",
            "",
        ).strip(),
        "gender": request.query_params.get(
            "gender",
            "",
        ).strip(),
        "country": request.query_params.get(
            "country",
            "",
        ).strip(),
        "campus": request.query_params.get(
            "campus",
            "",
        ).strip(),
        "term": request.query_params.get(
            "term",
            "",
        ).strip(),
        "status": request.query_params.get(
            "status",
            "",
        ).strip(),
        "decision": request.query_params.get(
            "decision",
            "",
        ).strip(),
    }

    filter_options = get_application_filter_options(
        user_role
    )

    applications = get_authorized_applications(
        user_role,
        filters,
    )

    active_filter_count = sum(
        bool(value)
        for value in filters.values()
    )

    return {
        "user_role": user_role,
        "filter_action": (
            f"/{user_role}/filter-applications"
        ),
        "applications": applications,
        "degree_options": filter_options[
            "degree_options"
        ],
        "term_options": filter_options[
            "term_options"
        ],
        "gender_options": GENDER_OPTIONS,
        "campus_options": CAMPUS_OPTIONS,
        "status_options": STATUS_OPTIONS,
        "decision_options": DECISION_OPTIONS,
        "filters": filters,
        "has_filters": active_filter_count > 0,
        "active_filter_count": active_filter_count,
        "result_count": len(applications),
    }


@router.get(
    "/administrator/filter-applications",
    response_class=HTMLResponse,
    name="administrator_filter_applications",
)
async def administrator_filter_applications(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="applications/filter_applications.html",
        context=get_filter_context(
            request,
            "administrator",
        ),
    )


@router.get(
    "/advisor/filter-applications",
    response_class=HTMLResponse,
    name="advisor_filter_applications",
)
async def advisor_filter_applications(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="applications/filter_applications.html",
        context=get_filter_context(
            request,
            "advisor",
        ),
    )