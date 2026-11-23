"""Graduate College admissions pages, printable correspondence and applicant intent."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.clients import database
from backend.service import accounts, admissions


router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")


def _actor(request, role):
    try:
        user = accounts.session_user(request.cookies.get("gdas_session", ""))
    except HTTPException as error:
        if error.status_code == 401:
            return None
        raise
    accounts.require_role(user, {role})
    return user


@router.get("/administrator/admissions", response_class=HTMLResponse)
async def administrator_admissions(request: Request, application: int | None = None):
    actor = _actor(request, "administrator")
    if actor is None:
        return RedirectResponse("/login", status_code=303)

    cases = admissions.list_cases(actor)
    selected = next((case for case in cases if case["id"] == application), None)
    if application is not None and selected is None:
        raise HTTPException(404, "Application not found")
    selected_record = (
        admissions.get_student_record(application, actor)
        if selected and selected["student_record_id"] is not None
        else None
    )
    return templates.TemplateResponse(
        request=request,
        name="administrator/admissions.html",
        context={
            "cases": cases,
            "selected": selected,
            "student_record": selected_record,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/administrator/admissions/{application_id}/letter",
    response_class=HTMLResponse,
)
async def printable_official_letter(request: Request, application_id: int):
    actor = _actor(request, "administrator")
    if actor is None:
        return RedirectResponse("/login", status_code=303)
    notice = admissions.get_notice_letter(application_id, actor)
    return templates.TemplateResponse(
        request=request,
        name="administrator/official_decision_letter.html",
        context={
            "notice": notice,
            "lines": notice["letter_body"].splitlines(),
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/administrator/admissions/{application_id}/student-record",
    response_class=HTMLResponse,
)
async def admitted_student_record(request: Request, application_id: int):
    actor = _actor(request, "administrator")
    if actor is None:
        return RedirectResponse("/login", status_code=303)
    record = admissions.get_student_record(application_id, actor)
    return templates.TemplateResponse(
        request=request,
        name="administrator/admitted_student_record.html",
        context={"record": record, "application_id": application_id},
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/administrator/admissions/{application_id}/registrar-notification",
    response_class=HTMLResponse,
)
async def registrar_simulation(request: Request, application_id: int):
    actor = _actor(request, "administrator")
    if actor is None:
        return RedirectResponse("/login", status_code=303)
    simulation = admissions.get_registrar_simulation(application_id, actor)
    return templates.TemplateResponse(
        request=request,
        name="administrator/registrar_notification.html",
        context={"simulation": simulation, "application_id": application_id},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/applicant/admission-offer", response_class=HTMLResponse)
async def applicant_admission_offer(request: Request, application_id: int):
    actor = _actor(request, "applicant")
    if actor is None:
        return RedirectResponse("/login", status_code=303)
    state = admissions.summary(application_id, actor)
    application = database.get_application(application_id)
    return templates.TemplateResponse(
        request=request,
        name="applicant/admission_offer.html",
        context={"state": state, "application": application},
        headers={"Cache-Control": "no-store"},
    )
