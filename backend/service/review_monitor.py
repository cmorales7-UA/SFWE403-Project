import os
from datetime import date, datetime

from fastapi import HTTPException

from backend.clients import database, reviewer_data
from backend.service import accounts, mailer


REMINDER_WINDOW_DAYS = 7
COMPLETED_RECOMMENDATIONS = {"recommend", "deny", "defer"}


def _require_access(actor):
    accounts.require_role(actor, {"advisor", "administrator"})


def _create_reminder_table(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS review_committee_reminders (
            id INTEGER PRIMARY KEY,
            assignment_id INTEGER NOT NULL,
            application_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            recipient_email TEXT NOT NULL,
            due_date TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_on TEXT NOT NULL,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (assignment_id, sent_on)
        )
        """
    )


def _parse_deadline(value):
    if not value:
        return None

    text = str(value).strip()

    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        try:
            return datetime.strptime(text, "%d/%m/%Y").date()
        except ValueError:
            return None


def _reminders_by_assignment():
    with database.connect() as db:
        _create_reminder_table(db)

        rows = db.execute(
            """
            SELECT assignment_id, recipient_email, sent_at, sent_on
            FROM review_committee_reminders
            ORDER BY id DESC
            """
        ).fetchall()

    history = {}

    for row in rows:
        history.setdefault(row["assignment_id"], []).append(dict(row))

    return history


def list_status(actor):
    """Return review status for applications the user can monitor."""

    _require_access(actor)

    apps = {
        item["id"]: item
        for item in database.applications()
    }

    users = {
        item["id"]: item
        for item in database.users()
    }

    reminders = _reminders_by_assignment()
    today = date.today()

    visible_programs = set(
        actor.get("assigned_program_ids") or []
    )

    is_admin = actor["user_type"] == "administrator"

    results = []

    for assignment in database.review_assignments():
        application = apps.get(assignment["application_id"])
        reviewer = users.get(assignment["reviewer_id"])

        if application is None or reviewer is None:
            continue

        if (
            not is_admin
            and application["program_id"] not in visible_programs
        ):
            continue

        review = reviewer_data.get_recommendation(
            application["id"],
            reviewer["id"],
        )

        choice = (review or {}).get("recommendation", "").lower()
        completed = choice in COMPLETED_RECOMMENDATIONS

        due_date = _parse_deadline(
            assignment.get("due_date")
        )

        days_left = (
            (due_date - today).days
            if due_date
            else None
        )

        recent = reminders.get(assignment["id"], [])

        sent_today = any(
            item["sent_on"] == today.isoformat()
            for item in recent
        )

        active = application.get("status") == "In Review"
        pending = not completed

        overdue = (
            pending
            and days_left is not None
            and days_left < 0
        )

        due_soon = (
            pending
            and days_left is not None
            and 0 <= days_left <= REMINDER_WINDOW_DAYS
        )

        eligible = (
            active
            and pending
            and due_date is not None
            and not sent_today
        )

        results.append({
            "assignment_id": assignment["id"],
            "application_id": application["id"],
            "applicant_name": application.get(
                "applicant_name", ""
            ),
            "degree_program": application.get(
                "degree_program",
                application.get("degree_name", ""),
            ),
            "application_status": application.get(
                "status", ""
            ),
            "reviewer_id": reviewer["id"],
            "reviewer_name": (
                f"{reviewer.get('first_name', '')} "
                f"{reviewer.get('last_name', '')}"
            ).strip(),
            "reviewer_email": reviewer.get("email", ""),
            "due_date": (
                due_date.isoformat()
                if due_date
                else assignment.get("due_date", "")
            ),
            "days_remaining": days_left,
            "review_status": (
                "Completed" if completed else "Pending"
            ),
            "recommendation": (
                choice.title() if completed else None
            ),
            "completed_at": (
                (review or {}).get("updated_at")
                if completed
                else None
            ),
            "due_soon": due_soon,
            "overdue": overdue,
            "reminder_eligible": eligible,
            "reminder_sent_today": sent_today,
            "last_reminded_at": (
                recent[0]["sent_at"] if recent else None
            ),
            "reminder_count": len(recent),
        })

    results.sort(
        key=lambda item: (
            item["review_status"] == "Completed",
            (
                item["days_remaining"]
                if item["days_remaining"] is not None
                else 99999
            ),
            item["applicant_name"].casefold(),
        )
    )

    return results


def send_reminder(assignment_id, actor):
    """Send a reminder for an outstanding review."""

    _require_access(actor)

    row = next(
        (
            item for item in list_status(actor)
            if item["assignment_id"] == assignment_id
        ),
        None,
    )

    if row is None:
        raise HTTPException(
            404,
            "Review assignment not found",
        )

    if row["review_status"] == "Completed":
        raise HTTPException(
            409,
            "The Reviewer has already submitted a recommendation",
        )

    if row["application_status"] != "In Review":
        raise HTTPException(
            409,
            "This application is no longer in review",
        )

    if row["days_remaining"] is None:
        raise HTTPException(
            409,
            "A valid review deadline is required",
        )

    if row["days_remaining"] > REMINDER_WINDOW_DAYS:
        raise HTTPException(
            409,
            f"Reminders are available within "
            f"{REMINDER_WINDOW_DAYS} days of the deadline",
        )

    if row["reminder_sent_today"]:
        raise HTTPException(
            409,
            "A reminder has already been sent today",
        )

    if (
        not row["reviewer_email"]
        or "@" not in row["reviewer_email"]
    ):
        raise HTTPException(
            409,
            "The Reviewer does not have a valid email address",
        )

    base_url = os.environ.get(
        "GDAS_BASE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    subject = (
        "UA-GDAS: Review Reminder - "
        f"{row['applicant_name']}"
    )

    if row["overdue"]:
        deadline_sentence = "The review deadline has passed."
    elif row["days_remaining"] == 0:
        deadline_sentence = "The review is due today."
    else:
        deadline_sentence = (
            f"The review is due in "
            f"{row['days_remaining']} day(s)."
        )

    body = (
        f"Hello {row['reviewer_name']},\n\n"
        "This is a reminder that your graduate "
        "application review is still pending.\n\n"
        f"Applicant: {row['applicant_name']}\n"
        f"Degree Program: {row['degree_program']}\n"
        f"Review Deadline: {row['due_date']}\n"
        f"{deadline_sentence}\n\n"
        "Open your assigned applications:\n"
        f"{base_url}/reviewer/applications"
        f"?application={row['application_id']}\n\n"
        "Please sign in with your Reviewer account "
        "and submit your recommendation.\n\n"
        "UA-GDAS"
    )

    # Do not mark the reminder sent until SMTP accepts it.
    mailer.send_email(
        row["reviewer_email"],
        subject,
        body,
    )

    with database.connect() as db:
        _create_reminder_table(db)

        db.execute(
            """
            INSERT INTO review_committee_reminders (
                assignment_id,
                application_id,
                reviewer_id,
                sender_id,
                recipient_email,
                due_date,
                subject,
                body,
                sent_on
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assignment_id,
                row["application_id"],
                row["reviewer_id"],
                actor["id"],
                row["reviewer_email"],
                row["due_date"],
                subject,
                body,
                date.today().isoformat(),
            ),
        )

    return {
        "status": "sent",
        "to": row["reviewer_email"],
        "assignment_id": assignment_id,
        "due_date": row["due_date"],
    }
