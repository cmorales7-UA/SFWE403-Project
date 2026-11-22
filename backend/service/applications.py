
"""Application access, preliminary review, and applicant communication (SRS 9.4)."""

from datetime import datetime, timezone
import json
import secrets

from fastapi import HTTPException

from backend.clients import database
from backend.service.accounts import require_role
from backend.service.security import hash_secret
from backend.service import mailer, graduate_college


FINAL_STATES = {"Accepted", "Denied"}

REVIEWABLE_STATUSES = {
    "Submitted",
    "Needs Information",
    "In Review",
}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Application Access and Permissions

def _access(application, actor):
    role = actor["user_type"]

    if role == "administrator":
        return

    if role == "applicant" and application["owner_id"] == actor["id"]:
        return

    if role == "advisor" and application["program_id"] in actor.get("assigned_program_ids", []):
        return

    raise HTTPException(
        403,
        "You are not authorized to access this application"
    )


def _public(application, actor):
    result = dict(application)

    if actor["user_type"] == "applicant":
        result.pop("review", None)
    elif actor["user_type"] == "advisor":
        # Graduate College notes are internal to Administrator review.
        review = dict(result.get("review") or {})
        for key in (
            "graduate_college_notes",
            "graduate_college_updated_by",
            "graduate_college_updated_at",
        ):
            review.pop(key, None)
        result["review"] = review

    return result


def get_application(application_id, actor):
    application = database.get_application(application_id)

    if application is None:
        raise HTTPException(404, "Application not found")

    _access(application, actor)

    return _public(application, actor)


def list_applications(actor):
    require_role(actor, {"applicant", "advisor", "administrator"})

    authorized = []

    for application in database.applications():
        try:
            _access(application, actor)
        except HTTPException:
            continue

        authorized.append(_public(application, actor))

    return authorized


# SRS 9.4.1 - Create and Update Applications

def create_application(payload, actor):
    require_role(actor, {"applicant"})

    program = next(
        (p for p in database.programs() if p["id"] == payload.program_id),
        None
    )

    if program is None:
        raise HTTPException(404, "Degree program not found")

    if payload.campus not in program["campus_offered"]:
        raise HTTPException(
            422,
            "Campus is not offered by the selected program"
        )

    if program.get("terms_offered") and payload.term not in program["terms_offered"]:
        raise HTTPException(
            422,
            "Term is not offered by the selected program"
        )

    application = {
        "owner_id": actor["id"],
        "program_id": program["id"],
        "degree_name": program["degree_name"],
        "degree_program": program["degree_name"],
        "applicant_name": f"{actor['first_name']} {actor['last_name']}",
        "full_name": f"{actor['first_name']} {actor['last_name']}",
        "email": actor["email"],
        "campus": payload.campus,
        "term": payload.term,
        "status": "Submitted" if payload.submitted else "In Process",
        "fields": payload.fields,
        "review": {},
        "last_updated": _now(),
        "submission_date": _now() if payload.submitted else "",
    }

    application_id = database.save_application(application)

    return get_application(application_id, actor)


def update_application(application_id, payload, actor):
    application = database.get_application(application_id)

    if application is None:
        raise HTTPException(404, "Application not found")

    _access(application, actor)

    if application["status"] in FINAL_STATES:
        raise HTTPException(
            409,
            "A final decision has already been made"
        )

    # Only editable form fields can change here.
    # Owner, program, decision, and authorization
    # metadata cannot be replaced by client-supplied JSON.
    application["fields"].update(payload.fields)

    application["last_updated"] = _now()

    database.save_application(application, application_id)

    return get_application(application_id, actor)


def save_graduate_college_review(application_id, payload, actor):
    """Save Administrator corrections in the existing review workflow."""
    require_role(actor, {"administrator"})

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT data FROM applications WHERE id=?", (application_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Application not found")

        application = json.loads(row["data"])
        if application.get("status") not in REVIEWABLE_STATUSES:
            raise HTTPException(409, "This application is no longer open for review")

        review = dict(application.get("review") or {})
        previous_comments = review.get("review_comments", "")
        new_comments = (
            payload.review_comments
            if payload.review_comments is not None else previous_comments
        )
        if payload.notes is not None:
            review["graduate_college_notes"] = payload.notes
        if payload.review_comments is not None:
            review["review_comments"] = payload.review_comments

        changed_review = (
            previous_comments != new_comments
            or (payload.notes is not None and
                payload.notes != review.get("graduate_college_notes", ""))
        )
        # Compare notes against the original before updating.
        if payload.notes is not None:
            original_review = json.loads(row["data"]).get("review") or {}
            changed_review = changed_review or (
                payload.notes != original_review.get("graduate_college_notes", "")
            )

        graduate_college.ensure_tables(db)
        decision_row = db.execute(
            "SELECT * FROM graduate_college_decisions WHERE application_id=?",
            (application_id,),
        ).fetchone()
        changed_decision = False

        if payload.decision is not None:
            if decision_row is None:
                raise HTTPException(
                    409, "The Advisor must submit a program recommendation first"
                )
            if (payload.decision_version is not None
                    and payload.decision_version != decision_row["version"]):
                raise HTTPException(
                    409, "The recommendation has changed. Refresh before saving"
                )
            changed_decision = (
                payload.decision != decision_row["decision"]
                or payload.rationale != decision_row["rationale"]
            )
            if changed_decision:
                official_table = db.execute(
                    """SELECT 1 FROM sqlite_master
                       WHERE type='table' AND name='official_admission_notices'"""
                ).fetchone()
                if official_table and db.execute(
                    """SELECT 1 FROM official_admission_notices
                       WHERE application_id=?""",
                    (application_id,),
                ).fetchone():
                    raise HTTPException(
                        409, "An official admission notice already exists for this application"
                    )
                db.execute(
                    """UPDATE graduate_college_decisions
                       SET decision=?, rationale=?, version=version+1,
                           updated_at=CURRENT_TIMESTAMP WHERE application_id=?""",
                    (payload.decision, payload.rationale, application_id),
                )

        if changed_review or changed_decision:
            db.execute(
                """CREATE TABLE IF NOT EXISTS graduate_college_admin_edit_history (
                       id INTEGER PRIMARY KEY,
                       application_id INTEGER NOT NULL,
                       administrator_id INTEGER NOT NULL,
                       previous_comments TEXT,
                       updated_comments TEXT,
                       previous_decision TEXT,
                       updated_decision TEXT,
                       previous_rationale TEXT,
                       updated_rationale TEXT,
                       edited_at TEXT NOT NULL
                   )"""
            )
            db.execute(
                """INSERT INTO graduate_college_admin_edit_history (
                       application_id, administrator_id, previous_comments,
                       updated_comments, previous_decision, updated_decision,
                       previous_rationale, updated_rationale, edited_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    application_id, actor["id"], previous_comments, new_comments,
                    decision_row["decision"] if decision_row else None,
                    payload.decision if payload.decision is not None
                    else (decision_row["decision"] if decision_row else None),
                    decision_row["rationale"] if decision_row else None,
                    payload.rationale if payload.rationale is not None
                    else (decision_row["rationale"] if decision_row else None),
                    _now(),
                ),
            )

        if changed_review or changed_decision:
            if payload.notes is not None or payload.review_comments is not None:
                review["graduate_college_updated_by"] = actor["id"]
                review["graduate_college_updated_at"] = _now()
            application["review"] = review
            application["last_updated"] = _now()
            db.execute(
                "UPDATE applications SET data=? WHERE id=?",
                (json.dumps(application), application_id),
            )

    result = get_application(application_id, actor)
    result["notification_required"] = changed_decision
    result["decision_version"] = (
        graduate_college.get_saved_decision(application_id) or {}
    ).get("version")
    return result


# SRS 9.4.2 - Preliminary Review Validation

def _require_preliminary_review_status(application):

    # Applications must be submitted before review.
    # Drafts and finalized applications cannot
    # enter the preliminary review process.
    if application["status"] not in REVIEWABLE_STATUSES:
        raise HTTPException(
            409,
            "This application is not available for preliminary review"
        )


# SRS 9.4.2 - Save Preliminary Review

def preliminary_review(application_id, payload, actor):
    require_role(actor, {"advisor"})

    application = get_application(application_id, actor)

    _require_preliminary_review_status(application)

    application["review"] = {
        "review_comments": payload.review_comments,
        "missing_information": payload.missing_information,
        "reviewer_id": actor["id"],
        "reviewed_at": _now(),
    }

    application["status"] = (
        "Needs Information"
        if payload.missing_information.strip()
        else "In Review"
    )

    application["last_updated"] = _now()

    database.save_application(application, application_id)

    return get_application(application_id, actor)


# Application Email Delivery

def _deliver(application, actor, subject, body, kind):

    mailer.send_email(
        application["email"],
        subject,
        body
    )

    database.save_message(
        application["id"],
        actor["id"],
        application["email"],
        kind,
        subject,
        body
    )

    return {
        "status": "sent",
        "to": application["email"],
    }


# SRS 9.4.2 - Request Missing Information

def request_information(application_id, actor):
    require_role(actor, {"advisor"})

    application = get_application(application_id, actor)

    _require_preliminary_review_status(application)

    missing = application.get(
        "review", {}
    ).get(
        "missing_information", ""
    ).strip()

    if not missing:
        raise HTTPException(
            422,
            "Save a preliminary review identifying missing information first"
        )

    subject = "UA-GDAS: Additional Application Information Required"

    body = (
        f"Hello {application['applicant_name']},\n\n"
        f"Additional information is required for your "
        f"{application['degree_name']} application:\n\n"
        f"{missing}\n\n"
        "Please log in to UA-GDAS to update your application.\n"
    )

    return _deliver(
        application,
        actor,
        subject,
        body,
        "missing_information"
    )


# SRS 9.4.3 - Application Communication

def message_applicant(application_id, payload, actor):
    require_role(actor, {"advisor", "administrator"})

    application = get_application(application_id, actor)

    if application["status"] in FINAL_STATES:
        raise HTTPException(
            409,
            "Communication for this workflow must occur before a final decision"
        )

    return _deliver(
        application,
        actor,
        payload.subject,
        payload.body,
        "applicant_message"
    )


# SRS 9.4.2 - Request Recommendation Letters

def request_recommendation(application_id, payload, actor):
    require_role(actor, {"advisor"})

    application = get_application(application_id, actor)

    _require_preliminary_review_status(application)

    number = payload.reference_number

    fields = application["fields"]

    name = fields.get(
        f"reference_{number}_name", ""
    ).strip()

    email = fields.get(
        f"reference_{number}_contact", ""
    ).strip()

    if (
        not name
        or not email
        or "@" not in email
        or "." not in email.rsplit("@", 1)[-1]
    ):
        raise HTTPException(
            422,
            "The applicant must provide a valid reference name and email"
        )

    # Generate unique credentials for the reference.
    login = "ref_" + secrets.token_hex(6)
    code = secrets.token_urlsafe(18)

    subject = "UA-GDAS: Letter of Recommendation Request"

    body = (
        f"Hello {name},\n\n"
        "You have been requested to provide a letter "
        f"of recommendation for {application['applicant_name']}'s "
        f"{application['degree_name']} application.\n\n"
        f"System-assigned login name: {login}\n"
        f"Authorization code: {code}\n\n"
        "Keep this authorization code private. "
        "A reference submission workflow must be enabled "
        "before the credentials can be used.\n"
    )

    # Send before persisting so delivery failures
    # do not produce false 'sent' records.
    mailer.send_email(
        email,
        subject,
        body
    )

    database.save_recommendation_request(
        application_id,
        actor["id"],
        number,
        name,
        email,
        login,
        hash_secret(code)
    )

    return {
        "status": "sent",
        "reference_number": number,
        "to": email,
        "login_name": login,
    }
