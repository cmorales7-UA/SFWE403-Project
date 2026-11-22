"""Database-backed application filtering for administrators and advisors."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.clients import database
from backend.service import accounts, applications, graduate_college


router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


def _normalize(value):
    """Compare form labels and stored values without case/space differences."""
    return str(value or "").strip().casefold()


def _application_gender(application):
    """Use only explicitly stored gender data; do not infer it from pronouns."""
    fields = application.get("fields") or {}
    return fields.get("gender") or fields.get("applicant_gender") or ""


def _application_country(application):
    fields = application.get("fields") or {}
    return fields.get("legal_residence_country") or ""


def _application_decision(application):
    # A final admissions result takes precedence over a program recommendation.
    status = application.get("status")
    if status in {"Accepted", "Denied"}:
        return status

    saved = graduate_college.get_saved_decision(application["id"])
    return saved["decision"] if saved else ""


def get_application_filter_options(actor, available):
    """Build real choices from the actor's authorized data and degree programs."""
    accounts.require_role(actor, {"administrator", "advisor"})

    permitted_programs = set(actor.get("assigned_program_ids") or [])
    programs = [
        program for program in database.programs()
        if actor["user_type"] == "administrator"
        or program["id"] in permitted_programs
    ]

    degree_options = {
        program.get("degree_name", "")
        for program in programs
        if program.get("degree_name")
    }
    degree_options.update(
        record.get("degree_program") or record.get("degree_name")
        for record in available
        if record.get("degree_program") or record.get("degree_name")
    )

    term_options = {
        term
        for program in programs
        for term in (program.get("terms_offered") or [])
        if term
    }
    term_options.update(
        record.get("term") for record in available if record.get("term")
    )

    def distinct(field):
        return sorted(
            {str(value).strip() for record in available
             if (value := field(record)) and str(value).strip()},
            key=str.casefold,
        )

    return {
        "degree_options": sorted(degree_options, key=str.casefold),
        "term_options": sorted(term_options, key=str.casefold),
        "status_options": distinct(lambda record: record.get("status")),
        "gender_options": distinct(_application_gender),
        "campus_options": sorted(
            {value.title() for value in distinct(lambda record: record.get("campus"))},
            key=str.casefold,
        ),
        "decision_options": distinct(lambda record: record.get("decision")),
    }


def get_authorized_applications(actor, filters, available=None):
    """Apply all requested filters to applications the current actor may view."""
    accounts.require_role(actor, {"administrator", "advisor"})
    if available is None:
        available = [
            dict(record, decision=_application_decision(record))
            for record in applications.list_applications(actor)
        ]

    results = []
    for application in available:
        if filters["degree"] and _normalize(
            application.get("degree_program") or application.get("degree_name")
        ) != _normalize(filters["degree"]):
            continue

        if filters["applicant_name"] and _normalize(filters["applicant_name"]) not in _normalize(
            application.get("applicant_name") or application.get("full_name")
        ):
            continue

        if filters["gender"] and _normalize(
            _application_gender(application)
        ) != _normalize(filters["gender"]):
            continue

        if filters["country"] and _normalize(filters["country"]) not in _normalize(
            _application_country(application)
        ):
            continue

        for field in ("campus", "term", "status", "decision"):
            if filters[field] and _normalize(
                application.get(field)
            ) != _normalize(filters[field]):
                break
        else:
            results.append(application)

    return results


def get_filter_context(request: Request, user_role: str, actor):
    """Retrieve current persisted records rather than returning empty fixtures."""
    accounts.require_role(actor, {user_role})

    filters = {
        key: request.query_params.get(key, "").strip()
        for key in (
            "degree", "applicant_name", "gender", "country",
            "campus", "term", "status", "decision",
        )
    }

    # The service performs the administrator/advisor ownership checks.
    available = [
        dict(record, decision=_application_decision(record))
        for record in applications.list_applications(actor)
    ]

    options = get_application_filter_options(actor, available)
    filtered = get_authorized_applications(actor, filters, available)

    return {
        "user_role": user_role,
        "filter_action": f"/{user_role}/filter-applications",
        "applications": filtered,
        **options,
        "filters": filters,
        "has_filters": any(filters.values()),
        "active_filter_count": sum(bool(value) for value in filters.values()),
        "result_count": len(filtered),
    }


def _current_user(request, required_role):
    user = accounts.session_user(request.cookies.get("gdas_session", ""))
    accounts.require_role(user, {required_role})
    return user


@router.get(
    "/administrator/filter-applications",
    response_class=HTMLResponse,
    name="administrator_filter_applications",
)
async def administrator_filter_applications(request: Request):
    try:
        actor = _current_user(request, "administrator")
    except HTTPException as error:
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

    return templates.TemplateResponse(
        request=request,
        name="applications/filter_applications.html",
        context=get_filter_context(request, "administrator", actor),
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/advisor/filter-applications",
    response_class=HTMLResponse,
    name="advisor_filter_applications",
)
async def advisor_filter_applications(request: Request):
    try:
        actor = _current_user(request, "advisor")
    except HTTPException as error:
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

    return templates.TemplateResponse(
        request=request,
        name="applications/filter_applications.html",
        context=get_filter_context(request, "advisor", actor),
        headers={"Cache-Control": "no-store"},
    )
