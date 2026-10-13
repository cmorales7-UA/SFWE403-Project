from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# Backend integration point.
def get_degree_programs():
    return []


def get_degree_program(degree_id: int):
    degree_programs = get_degree_programs()

    return next(
        (
            degree
            for degree in degree_programs
            if degree["id"] == degree_id
        ),
        None,
    )


def degree_browser_context(
    q: str,
    level: str,
    campus: str,
    degree: int | None,
):
    degree_programs = get_degree_programs()

    filtered_degrees = degree_programs.copy()

    search_query = q.strip().lower()

    if search_query:
        filtered_degrees = [
            item
            for item in filtered_degrees
            if search_query in item["name"].lower()
            or search_query in item["college"].lower()
        ]

    if level:
        filtered_degrees = [
            item
            for item in filtered_degrees
            if item["level_value"] == level
        ]

    if campus:
        filtered_degrees = [
            item
            for item in filtered_degrees
            if campus in item["campus_values"]
        ]

    selected_degree = None

    if degree is not None:
        selected_degree = next(
            (
                item
                for item in degree_programs
                if item["id"] == degree
            ),
            None,
        )

    return {
        "degrees": filtered_degrees,
        "selected_degree": selected_degree,
        "search_query": q,
        "selected_level": level,
        "selected_campus": campus,
    }


@router.get(
    "/applicant/graduate-degrees",
    response_class=HTMLResponse,
    name="applicant_graduate_degrees",
)
async def applicant_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/applicant/graduate-degrees"
    )

    context["degree_apply_action"] = (
        "/applicant/application"
    )

    return templates.TemplateResponse(
        request=request,
        name="applicant/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/administrator/graduate-degrees",
    response_class=HTMLResponse,
    name="administrator_graduate_degrees",
)
async def administrator_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/administrator/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="administrator/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/advisor/graduate-degrees",
    response_class=HTMLResponse,
    name="advisor_graduate_degrees",
)
async def advisor_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/advisor/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="advisor/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/reviewer/graduate-degrees",
    response_class=HTMLResponse,
    name="reviewer_graduate_degrees",
)
async def reviewer_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/reviewer/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="reviewer/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/it-support/graduate-degrees",
    response_class=HTMLResponse,
    name="it_support_graduate_degrees",
)
async def it_support_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/it-support/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="it_support/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/reference/graduate-degrees",
    response_class=HTMLResponse,
    name="reference_graduate_degrees",
)
async def reference_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/reference/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="reference/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/graduate-degrees",
    response_class=HTMLResponse,
    name="public_graduate_degrees",
)
async def public_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="degrees/public_degree_browser.html",
        context=context,
    )