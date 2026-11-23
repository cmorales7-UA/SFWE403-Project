"""Database-backed create and modify degree program pages."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.service import accounts, programs

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


def _current_role(request: Request, role: str):
    """Apply the same role checks as the existing program API."""
    try:
        actor = accounts.session_user(request.cookies.get("gdas_session", ""))
    except HTTPException as error:
        if error.status_code == 401:
            return None
        raise

    accounts.require_role(actor, {role})
    return actor


def _collaboration_context(actor):
    # The administrator may invite registered degree advisors to participate.
    return {
        "collaboration_advisors": sorted(
            (
                user for user in accounts.list_users(actor)
                if user["user_type"] == "advisor"
            ),
            key=lambda user: (
                (user.get("last_name") or "").casefold(),
                (user.get("first_name") or "").casefold(),
            ),
        ) if actor["user_type"] == "administrator" else [],
    }


def _modify_context(actor, degree_id: int | None):
    # Use existing database-backed program service, not fixtures.
    all_programs = programs.list_programs(actor)
    selected = (
        programs.get_program(degree_id, actor)
        if degree_id is not None
        else None
    )
    return {
        "degree_programs": sorted(
            all_programs,
            key=lambda item: item["degree_name"].casefold(),
        ),
        "selected_degree": selected,
        "change_history": (
            programs.change_history(degree_id, actor)
            if selected is not None else []
        ),
        **_collaboration_context(actor),
    }


@router.get(
    "/administrator/create-degree-program",
    response_class=HTMLResponse,
    name="administrator_create_degree_program",
)
async def administrator_create_degree_program(request: Request):
    actor = _current_role(request, "administrator")
    if actor is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="administrator/create_degree_program.html",
        context=_collaboration_context(actor),
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/advisor/create-degree-program",
    response_class=HTMLResponse,
    name="advisor_create_degree_program",
)
async def advisor_create_degree_program(request: Request):
    if _current_role(request, "advisor") is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="advisor/create_degree_program.html",
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/administrator/modify-degree-program",
    response_class=HTMLResponse,
    name="administrator_modify_degree_program",
)
async def administrator_modify_degree_program(
    request: Request,
    degree_id: int | None = None,
):
    actor = _current_role(request, "administrator")
    if actor is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="administrator/modify_degree_program.html",
        context=_modify_context(actor, degree_id),
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/advisor/modify-degree-program",
    response_class=HTMLResponse,
    name="advisor_modify_degree_program",
)
async def advisor_modify_degree_program(
    request: Request,
    degree_id: int | None = None,
):
    actor = _current_role(request, "advisor")
    if actor is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="advisor/modify_degree_program.html",
        context=_modify_context(actor, degree_id),
        headers={"Cache-Control": "no-store"},
    )
