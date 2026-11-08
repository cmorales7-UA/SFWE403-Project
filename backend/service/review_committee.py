import os
from collections import defaultdict
from datetime import date

from fastapi import HTTPException

from backend.clients import database
from backend.service import mailer
from backend.service.accounts import require_role


REVIEW_READY_STATUS = "In Review"


# Common Helpers
def _get_user(user_id):
    return next(
        (user for user in database.users() if user["id"] == user_id),
        None,
    )


def _get_application(application_id):
    application = database.get_application(application_id)

    if application is None:
        raise HTTPException(404, "Application not found")

    return application


def _advisor_application(application_id, actor):
    require_role(actor, {"advisor"})

    application = _get_application(application_id)

    if application["program_id"] not in actor.get(
        "assigned_program_ids", []
    ):
        raise HTTPException(
            403,
            "This application is outside your assigned degree programs",
        )

    return application


def _review_ready(application):
    if application.get("status") != REVIEW_READY_STATUS:
        raise HTTPException(
            409,
            "Only applications marked In Review can be assigned "
            "or sent to review committee members",
        )


def _reviewer_name(user):
    return " ".join(
        part for part in [
            user.get("first_name", ""),
            user.get("last_name", ""),
        ] if part
    ) or user["username"]


# Available Reviewers

def list_reviewers(actor):
    """Return eligible Reviewer accounts for an Advisor."""

    require_role(actor, {"advisor"})

    advisor_programs = set(
        actor.get("assigned_program_ids", [])
    )

    result = []

    for user in database.users():
        if user.get("user_type") != "reviewer":
            continue

        reviewer_programs = set(
            user.get("assigned_program_ids") or []
        )

        # If a reviewer has program restrictions, those
        # restrictions must overlap the Advisor's programs.
        if reviewer_programs and not (
            reviewer_programs & advisor_programs
        ):
            continue

        result.append({
            "id": user["id"],
            "name": _reviewer_name(user),
            "email": user["email"],
            "assigned_program_ids": sorted(reviewer_programs),
        })

    return result


# Create Reviewer Assignments

def create_assignments(payload, actor):
    """
    Assign selected applications to selected reviewers.

    Every selected reviewer receives every selected
    application, provided all access checks pass.
    """

    require_role(actor, {"advisor"})

    if payload.due_date < date.today():
        raise HTTPException(
            422,
            "The review deadline cannot be in the past",
        )

    applications = []

    for application_id in payload.application_ids:
        application = _advisor_application(
            application_id,
            actor,
        )

        _review_ready(application)
        applications.append(application)

    reviewers = []

    for reviewer_id in payload.reviewer_ids:
        reviewer = _get_user(reviewer_id)

        if reviewer is None:
            raise HTTPException(
                404,
                f"Reviewer {reviewer_id} was not found",
            )

        if reviewer.get("user_type") != "reviewer":
            raise HTTPException(
                422,
                f"User {reviewer_id} is not a Reviewer",
            )

        reviewer_programs = set(
            reviewer.get("assigned_program_ids") or []
        )

        if reviewer_programs:
            for application in applications:
                if application["program_id"] not in reviewer_programs:
                    raise HTTPException(
                        403,
                        "Reviewer is not authorized for one "
                        "or more selected degree programs",
                    )

        reviewers.append(reviewer)

    saved = []

    # All permissions are checked before writing.
    for application in applications:
        for reviewer in reviewers:
            assignment = database.save_review_assignment(
                application_id=application["id"],
                reviewer_id=reviewer["id"],
                assigned_by=actor["id"],
                due_date=payload.due_date.isoformat(),
            )

            saved.append(assignment)

    return {
        "status": "saved",
        "assignment_count": len(saved),
        "assignments": saved,
    }


# Retrieve Reviewer Assignments

def list_assignments(actor):
    """
    Advisor: assignments from managed programs.
    Reviewer: only their own assignments.
    Administrator: all assignments.

    This also establishes the data needed for
    SRS 9.4.6 monitoring.
    """

    require_role(
        actor,
        {"advisor", "reviewer", "administrator"},
    )

    if actor["user_type"] == "reviewer":
        records = database.review_assignments(
            reviewer_id=actor["id"]
        )
    else:
        records = database.review_assignments()

    users = {
        user["id"]: user
        for user in database.users()
    }

    result = []

    for record in records:
        application = database.get_application(
            record["application_id"]
        )

        if application is None:
            continue

        if actor["user_type"] == "advisor":
            if application["program_id"] not in actor.get(
                "assigned_program_ids", []
            ):
                continue

        reviewer = users.get(record["reviewer_id"])

        if reviewer is None:
            continue

        result.append({
            **record,
            "applicant_name": application.get(
                "applicant_name", ""
            ),
            "degree_program": application.get(
                "degree_program",
                application.get("degree_name", ""),
            ),
            "program_id": application["program_id"],
            "application_status": application.get(
                "status", ""
            ),
            "reviewer_name": _reviewer_name(reviewer),
            "reviewer_email": reviewer["email"],
        })

    return result



# Reviewer Application Access
def get_reviewer_application(application_id, actor):
    """
    Return an application only if the logged-in
    Reviewer has a matching assignment.

    Do not use the general applicant/advisor access
    function for this operation.
    """

    require_role(actor, {"reviewer"})

    assignments = database.review_assignments(
        application_id=application_id,
        reviewer_id=actor["id"],
    )

    if not assignments:
        raise HTTPException(
            403,
            "This application is not assigned to you",
        )

    application = _get_application(application_id)

    if application.get("status") != REVIEW_READY_STATUS:
        raise HTTPException(
            409,
            "This application is not currently available for review",
        )

    result = dict(application)

    # Advisor preliminary-review notes are internal.
    result.pop("review", None)

    result["review_assignment_id"] = assignments[0]["id"]
    result["review_deadline"] = assignments[0]["due_date"]

    return result


# SRS 9.4.4 - Email Notifications
def send_notifications(payload, actor):
    """
    Send one email per Reviewer.

    Each email lists the selected applications
    assigned to that Reviewer and their deadlines.
    """

    require_role(actor, {"advisor"})

    grouped = defaultdict(list)
    reviewers = {}

    # Validate every selected assignment before
    # sending any email.
    for assignment_id in payload.assignment_ids:
        assignment = database.get_review_assignment(
            assignment_id
        )

        if assignment is None:
            raise HTTPException(
                404,
                f"Assignment {assignment_id} was not found",
            )

        application = _advisor_application(
            assignment["application_id"],
            actor,
        )

        _review_ready(application)

        if assignment["notified_at"]:
            raise HTTPException(
                409,
                "One or more assignments have already "
                "received their initial notification",
            )

        reviewer = _get_user(
            assignment["reviewer_id"]
        )

        if reviewer is None or reviewer.get(
            "user_type"
        ) != "reviewer":
            raise HTTPException(
                422,
                "An assignment has an invalid Reviewer account",
            )

        reviewers[reviewer["id"]] = reviewer

        grouped[reviewer["id"]].append({
            "assignment": assignment,
            "application": application,
        })

    base_url = os.environ.get(
        "GDAS_BASE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    review_url = f"{base_url}/reviewer/applications"

    sent = []

    for reviewer_id, items in grouped.items():
        reviewer = reviewers[reviewer_id]

        items.sort(
            key=lambda item: (
                item["assignment"]["due_date"],
                item["application"]["id"],
            )
        )

        application_lines = []

        for item in items:
            application = item["application"]
            assignment = item["assignment"]

            deadline = date.fromisoformat(
                assignment["due_date"]
            ).strftime("%d/%m/%Y")

            application_lines.append(
                f"- {application.get('applicant_name', 'Applicant')}\n"
                f"  Degree Program: "
                f"{application.get('degree_program', application.get('degree_name', ''))}\n"
                f"  Review Deadline: {deadline}"
            )

        subject = "UA-GDAS: Applications Ready for Review"

        body = (
            f"Hello {_reviewer_name(reviewer)},\n\n"
            "Graduate applications have been assigned "
            "to you for review.\n\n"
            "Assigned Applications:\n\n"
            + "\n\n".join(application_lines)
            + "\n\n"
            "Access your assigned applications:\n"
            f"{review_url}\n\n"
            "Please complete your reviews by the "
            "specified deadlines.\n\n"
            "You must log in with your authorized "
            "Reviewer account to access these applications.\n\n"
            "UA-GDAS"
        )

        # SMTP delivery must succeed before recording
        # the notification as sent.
        mailer.send_email(
            reviewer["email"],
            subject,
            body,
        )

        assignment_ids = [
            item["assignment"]["id"]
            for item in items
        ]

        notification_id = database.save_review_notification(
            reviewer_id=reviewer_id,
            advisor_id=actor["id"],
            recipient=reviewer["email"],
            assignment_ids=assignment_ids,
            subject=subject,
            body=body,
            kind="initial",
        )

        sent.append({
            "notification_id": notification_id,
            "reviewer_id": reviewer_id,
            "recipient": reviewer["email"],
            "assignment_count": len(assignment_ids),
        })

    return {
        "status": "sent",
        "notifications_sent": len(sent),
        "notifications": sent,
    }
