
"""Graduate College decision notifications for SRS 9.4.5."""

import os

from fastapi import HTTPException

from backend.clients import database, reviewer_data
from backend.service import accounts, mailer


DECISIONS = {"Recommend", "Deny", "Defer"}


def ensure_tables(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS graduate_college_decisions (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL UNIQUE,
            advisor_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            rationale TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS graduate_college_notifications (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL,
            decision_version INTEGER NOT NULL,
            advisor_id INTEGER NOT NULL,
            administrator_id INTEGER NOT NULL,
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (
                application_id,
                decision_version,
                administrator_id
            )
        )
    """)


def advisor_application(application_id, actor):
    accounts.require_role(actor, {"advisor"})

    application = database.get_application(application_id)

    if application is None:
        raise HTTPException(404, "Application not found")

    assigned_programs = actor.get("assigned_program_ids") or []

    if application["program_id"] not in assigned_programs:
        raise HTTPException(
            403,
            "You are not authorized for this degree program",
        )

    if application["status"] != "In Review":
        raise HTTPException(
            409,
            "Only applications in review can receive a program decision",
        )

    return application


def get_saved_decision(application_id):
    with database.connect() as db:
        ensure_tables(db)

        row = db.execute(
            """
            SELECT *
            FROM graduate_college_decisions
            WHERE application_id = ?
            """,
            (application_id,),
        ).fetchone()

        return dict(row) if row else None


def get_notifications(application_id):
    with database.connect() as db:
        ensure_tables(db)

        return [
            dict(row)
            for row in db.execute(
                """
                SELECT *
                FROM graduate_college_notifications
                WHERE application_id = ?
                ORDER BY id DESC
                """,
                (application_id,),
            )
        ]


def committee_progress(application_id):
    assignments = [
        item for item in database.review_assignments()
        if item["application_id"] == application_id
    ]

    completed = 0

    for assignment in assignments:
        review = reviewer_data.get_recommendation(
            application_id,
            assignment["reviewer_id"],
        )

        if review and review.get("recommendation") in {
            "recommend",
            "deny",
            "defer",
        }:
            completed += 1

    return {
        "assigned": len(assignments),
        "completed": completed,
        "pending": len(assignments) - completed,
    }


def list_administrators(actor):
    accounts.require_role(actor, {"advisor"})

    return [
        {
            "id": user["id"],
            "name": (
                f"{user['first_name']} {user['last_name']}"
            ),
            "email": user["email"],
        }
        for user in database.users()
        if user["user_type"] == "administrator"
        and user.get("email")
    ]


def list_applications(actor):
    accounts.require_role(actor, {"advisor"})

    assigned_programs = set(
        actor.get("assigned_program_ids") or []
    )

    results = []

    for application in database.applications():
        if application["program_id"] not in assigned_programs:
            continue

        if application["status"] != "In Review":
            continue

        decision = get_saved_decision(application["id"])
        notifications = get_notifications(application["id"])
        progress = committee_progress(application["id"])

        sent = bool(
            decision
            and any(
                item["decision_version"] == decision["version"]
                for item in notifications
            )
        )

        results.append({
            "id": application["id"],
            "applicant_name": application["applicant_name"],
            "degree_program": application["degree_program"],
            "term": application["term"],
            "status": application["status"],
            "committee": progress,
            "decision": decision,
            "notified": sent,
        })

    return results


def get_details(application_id, actor):
    application = advisor_application(
        application_id,
        actor,
    )

    return {
        "application": {
            "id": application["id"],
            "applicant_name": application["applicant_name"],
            "degree_program": application["degree_program"],
            "term": application["term"],
            "status": application["status"],
        },
        "committee": committee_progress(application_id),
        "decision": get_saved_decision(application_id),
        "notifications": get_notifications(application_id),
    }


def save_decision(application_id, decision, rationale, actor):
    advisor_application(application_id, actor)

    if decision not in DECISIONS:
        raise HTTPException(
            422,
            "Decision must be Recommend, Deny, or Defer",
        )

    rationale = rationale.strip()

    if not rationale:
        raise HTTPException(
            422,
            "Enter a rationale for the program decision",
        )

    if len(rationale) > 5000:
        raise HTTPException(
            422,
            "Rationale cannot exceed 5000 characters",
        )

    with database.connect() as db:
        ensure_tables(db)

        existing = db.execute(
            """
            SELECT *
            FROM graduate_college_decisions
            WHERE application_id = ?
            """,
            (application_id,),
        ).fetchone()

        if existing is None:
            db.execute(
                """
                INSERT INTO graduate_college_decisions (
                    application_id,
                    advisor_id,
                    decision,
                    rationale
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    application_id,
                    actor["id"],
                    decision,
                    rationale,
                ),
            )

        elif (
            existing["decision"] != decision
            or existing["rationale"] != rationale
        ):
            db.execute(
                """
                UPDATE graduate_college_decisions
                SET advisor_id = ?,
                    decision = ?,
                    rationale = ?,
                    version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE application_id = ?
                """,
                (
                    actor["id"],
                    decision,
                    rationale,
                    application_id,
                ),
            )

    return get_details(application_id, actor)


def send_notification(application_id, administrator_id, actor):
    application = advisor_application(
        application_id,
        actor,
    )

    decision = get_saved_decision(application_id)

    if decision is None:
        raise HTTPException(
            409,
            "Save a program decision before notifying Graduate College",
        )

    administrator = next(
        (
            user for user in database.users()
            if user["id"] == administrator_id
            and user["user_type"] == "administrator"
        ),
        None,
    )

    if administrator is None:
        raise HTTPException(
            404,
            "Graduate College Administrator not found",
        )

    previous = get_notifications(application_id)

    if any(
        item["administrator_id"] == administrator_id
        and item["decision_version"] == decision["version"]
        for item in previous
    ):
        raise HTTPException(
            409,
            "This decision has already been sent to the selected Administrator",
        )

    progress = committee_progress(application_id)

    base_url = os.environ.get(
        "GDAS_BASE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    subject = (
        "UA-GDAS: Graduate Program Decision - "
        f"{application['applicant_name']}"
    )

    body = (
        f"Hello {administrator['first_name']},\n\n"
        "A graduate program decision is ready for Graduate "
        "College review.\n\n"
        f"Applicant: {application['applicant_name']}\n"
        f"Degree Program: {application['degree_program']}\n"
        f"Application ID: {application_id}\n"
        f"Academic Term: {application['term']}\n\n"
        f"Program Decision: {decision['decision']}\n\n"
        f"Advisor Rationale:\n{decision['rationale']}\n\n"
        "Review Committee:\n"
        f"Completed: {progress['completed']}\n"
        f"Assigned: {progress['assigned']}\n"
        f"Pending: {progress['pending']}\n\n"
        "Review the application:\n"
        f"{base_url}/administrator/application-review"
        f"?application={application_id}\n\n"
        "This is a graduate program recommendation, "
        "not a formal admissions decision.\n\n"
        "UA-GDAS"
    )

    # Record a notification only after SMTP accepts the message.
    mailer.send_email(
        administrator["email"],
        subject,
        body,
    )

    with database.connect() as db:
        ensure_tables(db)

        db.execute(
            """
            INSERT INTO graduate_college_notifications (
                application_id,
                decision_version,
                advisor_id,
                administrator_id,
                recipient_email,
                subject,
                body
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id,
                decision["version"],
                actor["id"],
                administrator_id,
                administrator["email"],
                subject,
                body,
            ),
        )

    return {
        "status": "sent",
        "to": administrator["email"],
        "application_id": application_id,
        "decision": decision["decision"],
        "version": decision["version"],
    }
