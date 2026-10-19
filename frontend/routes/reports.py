import csv
import io

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


REPORT_TYPES = {
    "current-applicants": "Current Degree Applicants Report",
    "applicant-status": "Degree Applicant Status Report",
}

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


def get_report_filter_options():
    """
    Backend integration point.

    Terms should eventually come from current application
    and degree-program data.
    """

    return {
        "term_options": [],
    }


def get_authorized_report_data(
    request: Request,
    report_type: str,
    filters: dict,
):
    """
    Backend integration point.

    The backend must verify that the current user is an
    authorized Graduate College Administrator before
    returning report data.
    """

    return []


def get_report_filters(request: Request):
    return {
        "term": request.query_params.get(
            "term",
            "",
        ).strip(),
        "campus": request.query_params.get(
            "campus",
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


def normalize_report_type(report_type: str):
    if report_type not in REPORT_TYPES:
        return "current-applicants"

    return report_type


def sanitize_csv_value(value):
    """
    Prevent spreadsheet applications from interpreting
    exported text as formulas.
    """

    if value is None:
        return ""

    text = str(value)

    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text

    return text


@router.get(
    "/administrator/reports",
    response_class=HTMLResponse,
    name="administrator_reports",
)
async def administrator_reports(request: Request):

    report_type = normalize_report_type(
        request.query_params.get(
            "report_type",
            "current-applicants",
        )
    )

    filters = get_report_filters(request)

    report_requested = (
        request.query_params.get("generate") == "1"
    )

    report_rows = []

    if report_requested:
        report_rows = get_authorized_report_data(
            request,
            report_type,
            filters,
        )

    filter_options = get_report_filter_options()

    return templates.TemplateResponse(
        request=request,
        name="administrator/reports.html",
        context={
            "report_types": REPORT_TYPES,
            "selected_report_type": report_type,
            "filters": filters,
            "term_options": filter_options[
                "term_options"
            ],
            "campus_options": CAMPUS_OPTIONS,
            "status_options": STATUS_OPTIONS,
            "decision_options": DECISION_OPTIONS,
            "report_requested": report_requested,
            "report_rows": report_rows,
            "result_count": len(report_rows),
        },
    )


@router.get(
    "/administrator/reports.csv",
    name="administrator_reports_csv",
)
async def administrator_reports_csv(request: Request):

    report_type = normalize_report_type(
        request.query_params.get(
            "report_type",
            "current-applicants",
        )
    )

    filters = get_report_filters(request)

    report_rows = get_authorized_report_data(
        request,
        report_type,
        filters,
    )

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(
        [
            "Applicant",
            "Degree Program",
            "Campus",
            "Term",
            "Application Status",
            "Decision",
        ]
    )

    for application in report_rows:
        writer.writerow(
            [
                sanitize_csv_value(
                    application.get("applicant_name")
                ),
                sanitize_csv_value(
                    application.get("degree_program")
                ),
                sanitize_csv_value(
                    application.get("campus")
                ),
                sanitize_csv_value(
                    application.get("term")
                ),
                sanitize_csv_value(
                    application.get("status")
                ),
                sanitize_csv_value(
                    application.get("decision")
                ),
            ]
        )

    filename = (
        "current-degree-applicants.csv"
        if report_type == "current-applicants"
        else "degree-applicant-status.csv"
    )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )