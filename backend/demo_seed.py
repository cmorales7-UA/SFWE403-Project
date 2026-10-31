
"""Create fictional local data for the UA-GDAS MPV1 demonstration."""

import os
from datetime import date
from pathlib import Path

from backend.clients import database
from backend.models.schemas import Registration, ProgramCreate
from backend.models.application_schemas import ApplicationCreate
from backend.service import accounts, applications


DEMO_DB = Path(__file__).resolve().parent / "data" / "mvp1_demo.sqlite3"
DEMO_PASSWORD = "DemoOnly123!"

# Use only the separate demonstration database.
os.environ["GDAS_DB_PATH"] = str(DEMO_DB)


def ensure_program(name, level, college, deadline):
    existing = next(
        (p for p in database.programs() if p["degree_name"] == name),
        None,
    )

    if existing:
        return existing

    program = ProgramCreate(
        degree_name=name,
        degree_level=level,
        degree_college=college,
        degree_description=f"Demonstration graduate program in {name}.",
        campus_offered=["main", "online"],
        terms_offered=["Fall 2027", "Spring 2028"],
        degree_requirements="Bachelor's degree and supporting materials.",
        application_deadline=deadline,
        application_fee="90.00",
        program_contact="graduate@example.test",
    )

    data = program.model_dump(mode="json")
    program_id = database.save_program(data)

    return dict(data, id=program_id)


def ensure_user(username, first_name, last_name, role, programs=None):
    existing = next(
        (u for u in database.users() if u["username"] == username),
        None,
    )

    if existing:
        return existing

    registration = Registration(
        username=username,
        password=DEMO_PASSWORD,
        security_question_1="Favorite color?",
        security_answer_1="Blue",
        security_question_2="Favorite animal?",
        security_answer_2="Cat",
        first_name=first_name,
        last_name=last_name,
        net_id="",
        phone="5205550100",
        email=f"{username}@example.test",
    )

    created = accounts.register(registration)

    user = next(
        u for u in database.users() if u["id"] == created["id"]
    )

    if role != "applicant":
        user_id = user.pop("id")
        user["user_type"] = role

        if programs is not None:
            user["assigned_program_ids"] = programs

        database.save_user(user, user_id)
        user["id"] = user_id

    return user


def application_fields(name, email, major, city):
    """Sample text fields matching the existing HTML application form."""
    return {
        "full_name": name,
        "preferred_pronoun": "",
        "date_of_birth": "2002-06-15",
        "mailing_address": f"Demo Address, {city}, Arizona",
        "email_address": email,
        "phone": "5205550100",
        "citizenship": "United States",
        "country_of_birth": "United States",
        "legal_residence_country": "United States",
        "visa": "",
        "military_affiliation": "no",
        "previous_ua_affiliation": "None",
        "resident_tuition_eligibility": "Yes",
        "education_degree_name": "Bachelor of Science",
        "university_name": "Example State University",
        "degree_type": "Bachelors",
        "degree_name": major,
        "total_credits": "120",
        "degree_start_date": "2020-08-20",
        "degree_received_date": "2024-05-15",
        "cumulative_gpa": "3.65",
        "reference_1_name": "Dr. Morgan Lee",
        "reference_1_title": "Professor",
        "reference_1_affiliation": "Example State University",
        "reference_1_contact": "morgan.lee@example.test",
        "reference_2_name": "Dr. Taylor Kim",
        "reference_2_title": "Associate Professor",
        "reference_2_affiliation": "Example State University",
        "reference_2_contact": "taylor.kim@example.test",
        "reference_3_name": "Jordan Smith",
        "reference_3_title": "Research Supervisor",
        "reference_3_affiliation": "Example Research Lab",
        "reference_3_contact": "jordan.smith@example.test",
        "sponsor_information": "No current sponsor.",
        "ta_ra_experience": "One year of undergraduate research.",
        "funding_information": "Interested in graduate assistantships.",
        "is_international_applicant": "no",
    }


def ensure_application(user, program, status, major, city, term):
    existing = next(
        (
            a for a in database.applications()
            if a["owner_id"] == user["id"]
            and a["program_id"] == program["id"]
            and a["term"] == term
        ),
        None,
    )

    if existing:
        return existing

    fields = application_fields(
        f"{user['first_name']} {user['last_name']}",
        user["email"],
        major,
        city,
    )

    payload = ApplicationCreate(
        program_id=program["id"],
        campus="main",
        term=term,
        fields=fields,
        submitted=status != "In Process",
    )

    created = applications.create_application(payload, user)

    if status == "In Review":
        saved = database.get_application(created["id"])
        saved["status"] = "In Review"
        database.save_application(saved, created["id"])

    return database.get_application(created["id"])


def main():
    software = ensure_program(
        "Software Engineering", "masters",
        "College of Engineering", date(2027, 5, 1)
    )

    computer_science = ensure_program(
        "Computer Science", "masters",
        "College of Science", date(2027, 4, 15)
    )

    avery = ensure_user(
        "demo_avery", "Avery", "Bennett", "applicant"
    )
    maya = ensure_user(
        "demo_maya", "Maya", "Thompson", "applicant"
    )
    jordan = ensure_user(
        "demo_jordan", "Jordan", "Rivera", "applicant"
    )

    ensure_user(
        "demo_admin", "Alex", "Administrator", "administrator"
    )

    ensure_user(
        "demo_advisor", "Taylor", "Advisor",
        "advisor", programs=[software["id"]]
    )

    records = [
        ensure_application(
            avery, software, "In Process",
            "Software Engineering", "Tucson", "Fall 2027"
        ),
        ensure_application(
            avery, computer_science, "Submitted",
            "Computer Science", "Tucson", "Spring 2028"
        ),
        ensure_application(
            maya, software, "Submitted",
            "Computer Engineering", "Yuma", "Fall 2027"
        ),
        ensure_application(
            jordan, computer_science, "In Review",
            "Computer Science", "Phoenix", "Fall 2027"
        ),
    ]

    print("\nUA-GDAS MPV1 demonstration database ready.")
    print(f"Database: {DEMO_DB}")
    print(f"Password for all demo accounts: {DEMO_PASSWORD}")
    print("\nDemo accounts:")
    for name in [
        "demo_avery", "demo_maya", "demo_jordan",
        "demo_admin", "demo_advisor"
    ]:
        print(f"  {name}")

    print("\nSample applications:")
    for record in records:
        print(
            f"  ID {record['id']}: "
            f"{record['applicant_name']} | "
            f"{record['degree_program']} | "
            f"{record['status']}"
        )


if __name__ == "__main__":
    main()
