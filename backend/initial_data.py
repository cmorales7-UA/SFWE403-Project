"""Initialize locally stored illustrative UA-GDAS accounts on first launch only.

Accounts are fictional coursework records, not verified university identities.
Messages must remain on a local test mail server.
"""
import os
import secrets
from datetime import date, datetime, timedelta, timezone

from backend.clients import database
from backend.models.schemas import Registration, ProgramCreate
from backend.service import accounts


PEOPLE = [
    ("avery.bennett", "Avery", "Bennett", "applicant", None),
    ("maya.thompson", "Maya", "Thompson", "applicant", None),
    ("jordan.rivera", "Jordan", "Rivera", "applicant", None),
    ("sophia.martinez", "Sophia", "Martinez", "applicant", None),
    ("liam.parker", "Liam", "Parker", "applicant", None),
    ("noah.walker", "Noah", "Walker", "applicant", None),
    ("olivia.reed", "Olivia", "Reed", "applicant", None),
    ("ethan.brooks", "Ethan", "Brooks", "applicant", None),
    ("alex.morgan", "Alex", "Morgan", "administrator", None),
    ("taylor.bennett", "Taylor", "Bennett", "advisor", "Software Engineering"),
    ("morgan.chen", "Morgan", "Chen", "advisor", "Computer Science"),
    ("elena.cruz", "Elena", "Cruz", "reviewer", "Software Engineering"),
    ("daniel.hayes", "Daniel", "Hayes", "reviewer", "Software Engineering"),
    ("priya.shah", "Priya", "Shah", "reviewer", "Computer Science"),
    ("casey.morgan", "Casey", "Morgan", "reference", None),
    ("jamie.taylor", "Jamie", "Taylor", "it_support", None),
]


def main():
    # Never seed into an already populated database.
    if database.users():
        return

    programs = {}
    for name, college, deadline in (
        ("Software Engineering", "College of Engineering", date(2027, 5, 1)),
        ("Computer Science", "College of Science", date(2027, 4, 15)),
    ):
        payload = ProgramCreate(
            degree_name=name,
            degree_level="masters",
            degree_college=college,
            degree_description=f"Graduate study and research in {name}.",
            campus_offered=["main", "online"],
            terms_offered=["Fall 2027", "Spring 2028"],
            degree_requirements="Bachelor's degree and required application materials.",
            application_deadline=deadline,
            application_fee="90.00",
            program_contact="gdas.programs@arizona.edu",
        )
        programs[name] = database.save_program(payload.model_dump(mode="json"))

    # Random local credentials, never a fixed password embedded in the source.
    password = os.environ.get("GDAS_STARTER_PASSWORD") or secrets.token_urlsafe(18)
    users = {}
    for username, first, last, role, area in PEOPLE:
        registration = Registration(
            username=username,
            password=password,
            security_question_1="First security question?",
            security_answer_1=secrets.token_urlsafe(18),
            security_question_2="Second security question?",
            security_answer_2=secrets.token_urlsafe(18),
            first_name=first,
            last_name=last,
            net_id=username.replace(".", ""),
            phone="5205550100",
            email=f"{username}@arizona.edu",
        )
        new_user = accounts.register(registration)
        record = next(user for user in database.users() if user["id"] == new_user["id"])
        if role != "applicant":
            record["user_type"] = role
        if area:
            record["assigned_program_ids"] = [programs[area]]
        user_id = record.pop("id")
        database.save_user(record, user_id)
        users[username] = user_id

    cases = [
        ("avery.bennett", "Software Engineering", "In Process"),
        ("maya.thompson", "Software Engineering", "Submitted"),
        ("sophia.martinez", "Software Engineering", "In Review"),
        ("liam.parker", "Software Engineering", "In Review"),
        ("noah.walker", "Software Engineering", "Needs Information"),
        ("olivia.reed", "Software Engineering", "Accepted"),
        ("jordan.rivera", "Computer Science", "In Review"),
        ("ethan.brooks", "Computer Science", "Denied"),
    ]
    created = {}
    for username, name, status in cases:
        first, last = username.split(".")
        review = {}
        if status in {"In Review", "Needs Information"}:
            review = {
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "review_comments": "Reviewed application documents.",
                "missing_information": (
                    "Confirm graduation date." if status == "Needs Information" else ""
                ),
            }
        application_id = database.save_application({
            "owner_id": users[username],
            "program_id": programs[name],
            "applicant_name": f"{first.title()} {last.title()}",
            "full_name": f"{first.title()} {last.title()}",
            "email": f"{username}@arizona.edu",
            "degree_name": name,
            "degree_program": name,
            "campus": "main",
            "term": "Fall 2027",
            "status": status,
            "review": review,
            "fields": {
                "full_name": f"{first.title()} {last.title()}",
                "email_address": f"{username}@arizona.edu",
                "legal_residence_country": "United States",
            },
        })
        created[username] = application_id

    due_date = (date.today() + timedelta(days=21)).isoformat()
    for user, reviewer, advisor in (
        ("sophia.martinez", "elena.cruz", "taylor.bennett"),
        ("liam.parker", "daniel.hayes", "taylor.bennett"),
        ("jordan.rivera", "priya.shah", "morgan.chen"),
    ):
        database.save_review_assignment(
            created[user], users[reviewer], users[advisor], due_date
        )

    print("UA-GDAS initial accounts are ready.")
    print("Illustrative account emails use @arizona.edu; no email delivery is implied.")
    print("Local account password:", password)
    print("Usernames:", ", ".join(record[0] for record in PEOPLE))


if __name__ == "__main__":
    main()
