"""Administrator reports built from current persisted graduate applications."""

import csv
import io
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from backend.clients import database
from backend.service import accounts, applications, graduate_college


router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

REPORT_TYPES = {
    "current-applicants": "Current Degree Applicants Report",
    "applicant-status": "Degree Applicant Status Report",
}
# Finalized applications belong to the status history report, not the
# current active applicant report.
FINAL_STATUSES = {"Accepted", "Denied"}


def _normalized(value):
    return str(value or "").strip().casefold()


def _current_administrator(request: Request):
    actor = accounts.session_user(request.cookies.get("gdas_session", ""))
    accounts.require_role(actor, {"administrator"})
    return actor


def normalize_report_type(report_type: str):
    return report_type if report_type in REPORT_TYPES else "current-applicants"


def get_report_filters(request: Request):
    return {
        field: request.query_params.get(field, "").strip()
        for field in ("term", "campus", "status", "decision")
    }


def _report_decision(application):
    # The final admission outcome, if present, takes priority over a program
    # recommendation stored in graduate_college_decisions.
    if application.get("status") in FINAL_STATUSES:
        return application["status"]
    saved = graduate_college.get_saved_decision(application["id"])
    return saved["decision"] if saved else ""


def _all_report_rows(actor):
    accounts.require_role(actor, {"administrator"})
    return [
        dict(application, decision=_report_decision(application))
        for application in applications.list_applications(actor)
    ]


def get_report_filter_options(actor, records=None):
    """Derive report filter choices from live applications and program data."""
    accounts.require_role(actor, {"administrator"})
    if records is None:
        records = _all_report_rows(actor)

    all_programs = database.programs()
    terms = {
        term for program in all_programs
        for term in (program.get("terms_offered") or [])
        if term
    }
    terms.update(row.get("term") for row in records if row.get("term"))

    campuses = {
        str(campus).title()
        for program in all_programs
        for campus in (program.get("campus_offered") or [])
        if campus
    }
    campuses.update(
        str(row.get("campus")).title()
        for row in records if row.get("campus")
    )

    return {
        "term_options": sorted(terms, key=str.casefold),
        "campus_options": sorted(campuses, key=str.casefold),
        "status_options": sorted({
            str(row["status"])
            for row in records if row.get("status")
        }, key=str.casefold),
        "decision_options": sorted({
            str(row["decision"])
            for row in records if row.get("decision")
        }, key=str.casefold),
    }


def get_authorized_report_data(actor, report_type: str, filters: dict, records=None):
    """Return only real authorized application rows matching all selected filters."""
    accounts.require_role(actor, {"administrator"})
    if records is None:
        records = _all_report_rows(actor)

    filtered = []
    for row in records:
        if report_type == "current-applicants" and row.get("status") in FINAL_STATUSES:
            continue
        if any(
            expected and _normalized(row.get(field)) != _normalized(expected)
            for field, expected in filters.items()
        ):
            continue
        filtered.append(row)
    return filtered


def sanitize_csv_value(value):
    """Prevent untrusted applicant values being evaluated as spreadsheet formulas."""
    if value is None:
        return ""
    value = str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


@router.get(
    "/administrator/reports",
    response_class=HTMLResponse,
    name="administrator_reports",
)
async def administrator_reports(request: Request):
    try:
        actor = _current_administrator(request)
    except HTTPException as error:
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

    report_type = normalize_report_type(
        request.query_params.get("report_type", "current-applicants")
    )
    filters = get_report_filters(request)
    requested = request.query_params.get("generate") == "1"

    records = _all_report_rows(actor)
    options = get_report_filter_options(actor, records)
    report_rows = (
        get_authorized_report_data(actor, report_type, filters, records)
        if requested else []
    )

    return templates.TemplateResponse(
        request=request,
        name="administrator/reports.html",
        context={
            "report_types": REPORT_TYPES,
            "selected_report_type": report_type,
            "filters": filters,
            **options,
            "report_requested": requested,
            "report_rows": report_rows,
            "result_count": len(report_rows),
            "report_csv_query": urlencode({
                "report_type": report_type, **filters,
            }),
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/administrator/reports.csv",
    name="administrator_reports_csv",
)
async def administrator_reports_csv(request: Request):
    actor = _current_administrator(request)
    report_type = normalize_report_type(
        request.query_params.get("report_type", "current-applicants")
    )
    report_rows = get_authorized_report_data(
        actor, report_type, get_report_filters(request)
    )

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "Applicant", "Degree Program", "Campus", "Term",
        "Application Status", "Decision",
    ])
    for row in report_rows:
        writer.writerow([
            sanitize_csv_value(row.get("applicant_name")),
            sanitize_csv_value(row.get("degree_program")),
            sanitize_csv_value(row.get("campus")),
            sanitize_csv_value(row.get("term")),
            sanitize_csv_value(row.get("status")),
            sanitize_csv_value(row.get("decision")),
        ])

    filename = (
        "current-degree-applicants.csv"
        if report_type == "current-applicants"
        else "degree-applicant-status.csv"
    )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
