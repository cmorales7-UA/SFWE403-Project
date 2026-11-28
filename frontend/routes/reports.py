"""SRS 9.6: program-scoped graduate application reports and analytics.

Reports contain persisted application data only. No student data is invented.
"""
import csv
import io
import sqlite3
from collections import Counter
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from backend.clients import database
from backend.service import accounts, applications, graduate_college


router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

REPORT_TYPES = {
    "current-submitted": "Current Graduate Applications",
    "tailored": "Tailored Application Report",
    "accepted-approved": "Accepted / Approved Applications",
    "denied-deferred": "Denied / Deferred Applications",
    "pending-review": "Pending / In Review Applications",
    "graphical": "Graphical Application Analysis",
    # Preserve URLs used by the earlier report pages.
    "current-applicants": "Current Degree Applicants Report",
    "applicant-status": "Degree Applicant Status Report",
}
# Keep legacy report URLs working without cluttering the new report selector.
VISIBLE_REPORT_TYPES = {
    key: label for key, label in REPORT_TYPES.items()
    if key not in {"current-applicants", "applicant-status"}
}
FINAL_STATUSES = {"Accepted", "Denied"}
PENDING_STATUSES = {"In Process", "Submitted", "In Review", "Needs Information"}

FIELD_GROUPS = {
    "Personal Information": [
        ("full_name", "Full Name"),
        ("preferred_pronoun", "Preferred Pronoun"),
        ("mailing_address", "Mailing Address"),
        ("email_address", "Email Address"),
        ("phone", "Phone"),
        ("date_of_birth", "Date of Birth"),
        ("citizenship", "Citizenship"),
        ("country_of_birth", "Country of Birth"),
        ("legal_residence_country", "Legal Residence Country"),
        ("visa", "Visa"),
        ("military_affiliation", "US Military Affiliation"),
        ("previous_ua_affiliation", "Previous UA Affiliation"),
        ("resident_tuition_eligibility", "Resident Tuition Eligibility"),
        ("gender", "Gender"),
    ],
    "Application Information": [
        ("degree_program", "Degree Program"),
        ("campus", "Campus"),
        ("term", "Term"),
        ("payment", "Payment"),
        ("submission_date", "Application Submission Date"),
        ("ethnicity", "Ethnicity"),
        ("application_status", "Application Status"),
        ("decision", "Decision"),
    ],
    "Education History": [
        ("education_degree_name", "Name of Degree"),
        ("university_name", "University Name"),
        ("degree_type", "Degree Type"),
        ("degree_name", "Degree Name"),
        ("total_credits", "Total Credits"),
        ("degree_start_date", "Date Degree Started"),
        ("degree_received_date", "Date Degree Received"),
        ("cumulative_gpa", "Cumulative GPA"),
        ("official_transcripts", "Official Transcripts"),
    ],
    "Supporting Documents": [
        ("application_fee_payment", "Application Fee Payment Information"),
        ("resume", "Curriculum Vitae / Resume"),
        ("personal_statement", "Personal Statement Essay"),
    ],
    "Letters of Recommendation": [
        (f"reference_{n}_{part}", f"Reference {n} {label}")
        for n in (1, 2, 3)
        for part, label in (
            ("name", "Name"), ("title", "Title"),
            ("affiliation", "Affiliation"), ("contact", "Contact"),
        )
    ],
    "Supplemental Questions": [
        ("sponsor_information", "Program Sponsor"),
        ("ta_ra_experience", "TA / RA Experience"),
        ("funding_information", "Funding Requirements"),
        ("is_international_applicant", "International Applicant"),
        ("english_test_date", "English Test Month and Year"),
        ("english_proficiency_score", "English Proficiency Score"),
        ("program_questions", "Program-Specific Answers"),
    ],
}
FIELD_LABELS = dict(field for group in FIELD_GROUPS.values() for field in group)
SUMMARY_COLUMNS = ("full_name", "degree_program", "campus", "term", "application_status", "decision")
# SRS 9.6.3-9.6.4 require personal, application, education and ethnicity.
DECISION_COLUMNS = tuple(key for group in (
    "Personal Information", "Application Information", "Education History"
) for key, _ in FIELD_GROUPS[group])
DETAIL_COLUMNS = tuple(FIELD_LABELS)
GRAPH_TYPES = {
    "degree_program": "Applications by Degree Program",
    "ethnicity": "Applicants by Ethnicity",
    "legal_residence_country": "Applicants by Country of Legal Residence",
    "gender": "Applicants by Gender",
    "campus": "Applicants by Campus",
    "degree_type": "Applicants by Previous Degree Type",
    "ua_degree": "Previous Degree from University of Arizona",
    "term": "Applicants by Application Term",
    "application_status": "Applicants by Application Status",
}
FILTER_LABELS = {
    "term": "Term", "campus": "Campus", "status": "Application Status",
    "decision": "Decision", "full_name": "Full Name",
    "citizenship": "Citizenship", "visa": "Visa",
    "military_affiliation": "US Military Affiliation",
    "previous_ua_affiliation": "Previous UA Affiliation",
    "resident_tuition_eligibility": "Resident Tuition Eligibility",
    "ethnicity": "Ethnicity", "sponsor_information": "Program Sponsor",
    "ta_ra_experience": "TA / RA Experience",
    "funding_information": "Funding Requirements",
    "is_international_applicant": "International Applicant",
    "english_test_date": "English Proficiency Test Date",
    "english_proficiency_score": "English Proficiency Score",
    "program_questions": "Program-Specific Answers",
}
# SRS 9.6.2 filter groups. Other application fields remain selectable as
# report columns, but are not available as filtering criteria.
TAILORED_FILTER_GROUPS = {
    "Applicant details": (
        "full_name", "citizenship", "visa", "military_affiliation",
        "previous_ua_affiliation", "resident_tuition_eligibility", "ethnicity",
    ),
    "Supplemental questions": (
        "sponsor_information", "ta_ra_experience", "funding_information",
        "program_questions",
    ),
    "English proficiency (international applicants)": (
        "english_test_date", "english_proficiency_score",
    ),
}
TAILORED_STATUS_OPTIONS = ("In Process", "Submitted", "In Review")
TAILORED_DECISION_OPTIONS = ("Recommend", "Defer", "Deny", "Intent to Matriculate")
# These are free-text filters; dropdowns are created for the remaining filters.
TEXT_FILTERS = ("full_name", "citizenship", "visa", "sponsor_information",
                "ta_ra_experience", "funding_information", "english_test_date",
                "english_proficiency_score", "program_questions")


def _normalized(value):
    return str(value or "").strip().casefold()


def _text(value):
    if value is None:
        return ""
    if isinstance(value, (tuple, list)):
        return "; ".join(_text(item) for item in value)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_text(item)}" for key, item in value.items())
    return str(value)


def _report_actor(request: Request):
    actor = accounts.session_user(request.cookies.get("gdas_session", ""))
    accounts.require_role(actor, {"administrator", "advisor"})
    route_role = "advisor" if request.url.path.startswith("/advisor/") else "administrator"
    accounts.require_role(actor, {route_role})
    return actor, route_role


def normalize_report_type(report_type: str):
    return report_type if report_type in REPORT_TYPES else "current-submitted"


def get_report_filters(request: Request):
    return {
        field: request.query_params.get(field, "").strip()[:300]
        for field in FILTER_LABELS
    }


def _report_decision(application, saved=None):
    if application.get("status") in FINAL_STATUSES:
        return application["status"]
    if application.get("status") == "Intent to Matriculate":
        return "Intent to Matriculate"
    if saved is None:
        saved = graduate_college.get_saved_decision(application["id"])
    return saved["decision"] if saved else ""


def _official_transcript_names():
    """Only include filename metadata; no private file contents or paths."""
    try:
        with database.connect() as db:
            return {row["application_id"]: row["filename"] for row in db.execute(
                "SELECT application_id, filename FROM official_transcripts"
            )}
    except sqlite3.OperationalError:
        return {}


def _all_report_rows(actor):
    accounts.require_role(actor, {"administrator", "advisor"})
    programs = {item["id"]: item for item in database.programs()}
    transcript_names = _official_transcript_names()
    rows = []
    for application in applications.list_applications(actor):
        fields = application.get("fields") or {}
        program = programs.get(application["program_id"], {})
        saved = graduate_college.get_saved_decision(application["id"])
        values = {key: _text(fields.get(key)) for key in FIELD_LABELS}
        values.update({
            "full_name": _text(application.get("full_name") or application.get("applicant_name")
                               or fields.get("full_name")),
            "email_address": _text(fields.get("email_address") or application.get("email")),
            "phone": _text(fields.get("phone")),
            "degree_program": _text(application.get("degree_program") or program.get("degree_name")),
            "campus": _text(application.get("campus")),
            "term": _text(application.get("term")),
            "payment": _text(fields.get("payment") or application.get("payment")),
            "submission_date": _text(application.get("submission_date")),
            "application_status": _text(application.get("status")),
            "decision": _report_decision(application, saved),
            "gender": _text(fields.get("gender") or fields.get("applicant_gender")),
            "application_fee_payment": _text(
                fields.get("application_fee_payment") or application.get("payment")
            ),
            "official_transcripts": _text(fields.get("official_transcripts")
                                          or transcript_names.get(application["id"])),
        })
        questions = []
        for question in (program.get("application_questions") or []):
            if not isinstance(question, dict):
                continue
            answer = fields.get(str(question.get("id", "")))
            if answer:
                questions.append(f'{question.get("text") or "Question"}: {_text(answer)}')
        values["program_questions"] = "; ".join(questions)
        # Track the advisor's recommendation separately from the formal decision.
        category = ("Intent to Matriculate" if application.get("status") == "Intent to Matriculate"
                    else (saved.get("decision") if saved else
                          "Deny" if application.get("status") == "Denied" else
                          "Recommend" if application.get("status") == "Accepted" else ""))
        rows.append({
            **application,
            "decision": values["decision"],
            "decision_category": category,
            "values": values,
        })
    return rows


def _programs_for(actor):
    program_ids = set(actor.get("assigned_program_ids") or [])
    return sorted(
        [dict(id=p["id"], name=p.get("degree_name", "Unnamed program"))
         for p in database.programs()
         if actor["user_type"] == "administrator" or p["id"] in program_ids],
        key=lambda p: p["name"].casefold(),
    )


def get_report_filter_options(actor, records=None):
    accounts.require_role(actor, {"administrator", "advisor"})
    if records is None:
        records = _all_report_rows(actor)
    programs = _programs_for(actor)
    options = {
        "program_options": programs,
        "term_options": sorted({r.get("term") for r in records if r.get("term")},
                               key=str.casefold),
        "campus_options": sorted({str(r.get("campus")).title() for r in records
                                  if r.get("campus")}, key=str.casefold),
        "status_options": sorted({r.get("status") for r in records if r.get("status")},
                                 key=str.casefold),
        "decision_options": sorted({r.get("decision") for r in records if r.get("decision")}
                                   | {"Recommend", "Defer", "Deny", "Intent to Matriculate"},
                                   key=str.casefold),
        "tailored_filters": {},
    }
    for field in FILTER_LABELS:
        if field in TEXT_FILTERS or field in {"term", "campus", "status", "decision"}:
            continue
        choices = {r["values"].get(field) for r in records if r["values"].get(field)}
        options["tailored_filters"][field] = sorted(choices, key=str.casefold)
    return options


def _matches(row, filters):
    values = row["values"]
    for name, expected in filters.items():
        if not expected:
            continue
        if name == "status":
            actual = row.get("status")
        elif name == "decision":
            actual = row["decision_category"]
            if _normalized(actual) != _normalized(expected):
                actual = row.get("decision")
        elif name in TEXT_FILTERS:
            if _normalized(expected) not in _normalized(values.get(name)):
                return False
            continue
        else:
            actual = values.get(name)
        if _normalized(actual) != _normalized(expected):
            return False
    return True


def get_authorized_report_data(actor, report_type: str, filters: dict, records=None,
                               program_id=""):
    accounts.require_role(actor, {"administrator", "advisor"})
    if report_type == "tailored" and not program_id:
        raise HTTPException(422, "Select a degree program to generate a tailored report")
    if report_type == "tailored":
        if filters.get("status") and filters["status"] not in TAILORED_STATUS_OPTIONS:
            raise HTTPException(422, "Invalid tailored application status filter")
        if filters.get("decision") and filters["decision"] not in TAILORED_DECISION_OPTIONS:
            raise HTTPException(422, "Invalid tailored application decision filter")
    if records is None:
        records = _all_report_rows(actor)
    result = []
    for row in records:
        if program_id and str(row.get("program_id")) != str(program_id):
            continue
        status = row.get("status", "")
        category = row["decision_category"]
        if report_type == "current-applicants" and status in FINAL_STATUSES:
            continue
        if report_type == "current-submitted" and status == "In Process":
            continue
        if report_type == "accepted-approved" and not (
            category in {"Recommend", "Intent to Matriculate"}
        ):
            continue
        if report_type == "denied-deferred" and not (
            status == "Denied" or category in {"Deny", "Defer"}
        ):
            continue
        if report_type == "pending-review" and status not in PENDING_STATUSES:
            continue
        if _matches(row, filters):
            result.append(row)
    return result


def _columns(report_type, selected):
    if report_type == "tailored":
        valid = [column for column in selected if column in FIELD_LABELS]
        return tuple(dict.fromkeys(valid)) or SUMMARY_COLUMNS
    if report_type in {"current-submitted", "pending-review"}:
        return DETAIL_COLUMNS
    if report_type in {"accepted-approved", "denied-deferred"}:
        return DECISION_COLUMNS
    return SUMMARY_COLUMNS


def _graph_data(rows, graph_type):
    metric = graph_type if graph_type in GRAPH_TYPES else "degree_program"
    counts = Counter()
    for row in rows:
        if metric == "ua_degree":
            university = _normalized(row["values"].get("university_name"))
            value = ("Yes" if university and ("university of arizona" in university
                                              or university == "u of a")
                     else "No" if university else "Not provided")
        else:
            value = row["values"].get(metric) or "Not provided"
        counts[str(value)] += 1
    biggest = max(counts.values(), default=1)
    return [{
        "label": label, "count": count,
        "percent": round(100 * count / biggest),
    } for label, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))]


def sanitize_csv_value(value):
    """Prevent Excel/Sheets formula execution from untrusted applicant fields."""
    value = _text(value)
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def _report_state(request, actor):
    report_type = normalize_report_type(request.query_params.get("report_type", "current-submitted"))
    filters = get_report_filters(request)
    if report_type != "tailored":
        # Filters hidden in non-tailored reports must not change the results.
        visible_filters = {"campus", "term", "status", "decision"}
        filters = {key: value if key in visible_filters else ""
                   for key, value in filters.items()}
    program_id = request.query_params.get("program_id", "").strip()
    selected = request.query_params.getlist("fields")
    graph_type = request.query_params.get("graph_type", "degree_program")
    if graph_type not in GRAPH_TYPES:
        graph_type = "degree_program"
    records = _all_report_rows(actor)
    # A blank tailored selection is an empty form, not an all-program report.
    rows = (get_authorized_report_data(actor, report_type, filters, records, program_id)
            if report_type != "tailored" or program_id else [])
    query = urlencode({
        "report_type": report_type, "program_id": program_id,
        **filters, "fields": [f for f in selected if f in FIELD_LABELS],
        "graph_type": graph_type,
    }, doseq=True)
    return report_type, filters, program_id, selected, graph_type, records, rows, query


@router.get("/administrator/reports", response_class=HTMLResponse,
            name="administrator_reports")
@router.get("/advisor/reports", response_class=HTMLResponse, name="advisor_reports")
async def reports_page(request: Request):
    try:
        actor, role = _report_actor(request)
    except HTTPException as error:
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise
    report_type, filters, program_id, selected, graph_type, records, rows, query = (
        _report_state(request, actor)
    )
    requested = request.query_params.get("generate") == "1"
    form_error = ("Select a degree program to generate a tailored report."
                  if requested and report_type == "tailored" and not program_id else None)
    columns = _columns(report_type, selected)
    options = get_report_filter_options(actor, records)
    return templates.TemplateResponse(
        request=request,
        name="administrator/reports.html",
        context={
            "role": role, "report_types": REPORT_TYPES,
            "report_type_options": VISIBLE_REPORT_TYPES,
            "selected_report_type": report_type,
            "filters": filters, "program_id": program_id,
            "selected_fields": selected, "field_groups": FIELD_GROUPS,
            "field_labels": FIELD_LABELS, "filter_labels": FILTER_LABELS,
            "text_filters": TEXT_FILTERS,
            "tailored_filter_groups": TAILORED_FILTER_GROUPS,
            "tailored_status_options": TAILORED_STATUS_OPTIONS,
            "tailored_decision_options": TAILORED_DECISION_OPTIONS,
            "form_error": form_error,
            "report_requested": requested, "report_rows": rows if requested else [],
            "result_count": len(rows) if requested else 0,
            "columns": columns if report_type == "tailored" else SUMMARY_COLUMNS,
            "detail_columns": columns if report_type != "tailored" else (),
            "report_csv_query": query, "graph_types": GRAPH_TYPES,
            "selected_graph_type": graph_type,
            "graph_data": _graph_data(rows, graph_type) if requested and report_type == "graphical" else [],
            **options,
        },
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/administrator/reports.csv", name="administrator_reports_csv")
@router.get("/advisor/reports.csv", name="advisor_reports_csv")
async def reports_csv(request: Request):
    actor, _ = _report_actor(request)
    report_type, filters, program_id, selected, graph_type, records, rows, _ = (
        _report_state(request, actor)
    )
    if report_type == "tailored" and not program_id:
        raise HTTPException(422, "Select a degree program to generate a tailored report")
    columns = _columns(report_type, selected)
    legacy = report_type in {"current-applicants", "applicant-status"}
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    if report_type == "graphical":
        writer.writerow(["Category", "Application Count"])
        for item in _graph_data(rows, graph_type):
            writer.writerow([sanitize_csv_value(item["label"]), item["count"]])
    else:
        writer.writerow([
            ("Applicant" if legacy and key == "full_name" else
             "Application Status" if legacy and key == "application_status" else
             FIELD_LABELS[key])
            for key in columns
        ])
        for row in rows:
            writer.writerow([sanitize_csv_value(row["values"].get(key)) for key in columns])
    names = {
        "current-applicants": "current-degree-applicants",
        "applicant-status": "degree-applicant-status",
    }
    filename = names.get(report_type, report_type) + ".csv"
    return Response(
        content=output.getvalue(), media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
