from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


def degree_browser_context(
    q: str,
    level: str,
    campus: str,
):
    return {
        "degrees": [],
        "selected_degree": None,
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
    return templates.TemplateResponse(
        request=request,
        name="applicant/graduate_degrees.html",
        context=degree_browser_context(q, level, campus),
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
    return templates.TemplateResponse(
        request=request,
        name="administrator/graduate_degrees.html",
        context=degree_browser_context(q, level, campus),
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
    return templates.TemplateResponse(
        request=request,
        name="advisor/graduate_degrees.html",
        context=degree_browser_context(q, level, campus),
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
    return templates.TemplateResponse(
        request=request,
        name="reviewer/graduate_degrees.html",
        context=degree_browser_context(q, level, campus),
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
    return templates.TemplateResponse(
        request=request,
        name="it_support/graduate_degrees.html",
        context=degree_browser_context(q, level, campus),
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
    return templates.TemplateResponse(
        request=request,
        name="reference/graduate_degrees.html",
        context=degree_browser_context(q, level, campus),
    )