import os

from fastapi import HTTPException

from backend.clients import database, reviewer_data
from backend.service import accounts, mailer


def assigned_application(application_id, actor):
    accounts.require_role(actor, {"reviewer"})

    application = database.get_application(application_id)

    if application is None:
        raise HTTPException(404, "Application not found")

    assignments = database.review_assignments()

    assignment = next(
        (
            item for item in assignments
            if item["application_id"] == application_id
            and item["reviewer_id"] == actor["id"]
        ),
        None,
    )

    if assignment is None:
        raise HTTPException(403, "This application is not assigned to you")

    allowed_programs = actor.get("assigned_program_ids") or []

    if application["program_id"] not in allowed_programs:
        raise HTTPException(403, "You are not assigned to this degree program")

    if application["status"] != "In Review":
        raise HTTPException(
            409,
            "This application is not currently available for review",
        )

    return application, assignment


def get_review(application_id, actor):
    assigned_application(application_id, actor)

    saved = reviewer_data.get_recommendation(
        application_id,
        actor["id"],
    )

    messages = []

    for item in database.messages(application_id):
        sent_by_reviewer = (
            item["kind"] == "reviewer_advisor"
            and item["actor_id"] == actor["id"]
        )

        received_from_advisor = (
            item["kind"] == "advisor_reviewer"
            and item["recipient"].casefold() == actor["email"].casefold()
        )

        if not sent_by_reviewer and not received_from_advisor:
            continue

        messages.append({
            "sender_name": (
                "You" if sent_by_reviewer else "Degree Advisor"
            ),
            "timestamp": item["sent_at"],
            "content": item["body"],
        })

    return {
        "recommendation": saved["recommendation"] if saved else "",
        "comments": saved["comments"] if saved else "",
        "updated_at": saved["updated_at"] if saved else None,
        "messages": messages,
    }


def list_reviews(actor):
    accounts.require_role(actor, {"reviewer"})

    assigned_ids = {
        item["application_id"]
        for item in database.review_assignments()
        if item["reviewer_id"] == actor["id"]
    }

    return {
        str(item["application_id"]): item["recommendation"]
        for item in reviewer_data.list_recommendations(actor["id"])
        if item["application_id"] in assigned_ids
    }


def save_recommendation(
    application_id,
    recommendation,
    comments,
    actor,
):
    assigned_application(application_id, actor)

    return reviewer_data.save_recommendation(
        application_id,
        actor["id"],
        recommendation,
        comments,
    )


def send_message(application_id, message, actor):
    application, assignment = assigned_application(
        application_id,
        actor,
    )

    advisor = next(
        (
            user for user in database.users()
            if user["id"] == assignment["assigned_by"]
            and user["user_type"] == "advisor"
            and application["program_id"]
                in (user.get("assigned_program_ids") or [])
        ),
        None,
    )

    if advisor is None:
        raise HTTPException(
            409,
            "An authorized Advisor could not be found for this assignment",
        )

    subject = (
        "UA-GDAS: Reviewer Message - "
        f"{application['applicant_name']}"
    )

    base_url = os.environ.get(
        "GDAS_BASE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")

    body = (
        f"Hello {advisor['first_name']},\n\n"
        f"{actor['first_name']} {actor['last_name']} sent a message "
        f"about the following application:\n\n"
        f"Applicant: {application['applicant_name']}\n"
        f"Degree Program: {application['degree_program']}\n"
        f"Application ID: {application_id}\n\n"
        f"Message:\n{message}\n\n"
        "View the application:\n"
        f"{base_url}/advisor/application-review"
        f"?application={application_id}\n\n"
        "UA-GDAS"
    )

    mailer.send_email(advisor["email"], subject, body)

    database.save_message(
        application_id,
        actor["id"],
        advisor["email"],
        "reviewer_advisor",
        subject,
        message,
    )

    return {
        "status": "sent",
        "to": advisor["email"],
    }