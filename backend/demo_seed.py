
"""Create persistent test data for UA-GDAS."""

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


DEMO_DB = Path(__file__).resolve().parent / "data" / "mvp1_demo.sqlite3"
DEMO_PASSWORD = "DemoOnly123!"
DEMO_DOMAIN = "arizona.edu"

# Select the demo database before loading backend modules.
os.environ["GDAS_DB_PATH"] = str(DEMO_DB)

from backend.clients import database
from backend.models.application_schemas import ApplicationCreate
from backend.models.schemas import ProgramCreate, Registration
from backend.service import accounts, applications


def demo_email(username):
    return f"{username}@{DEMO_DOMAIN}"


def ensure_program(name, level, college, deadline):
    existing = next(
        (p for p in database.programs() if p["degree_name"] == name),
        None,
    )

    if existing:
        if existing.get("program_contact") == "graduate@example.test":
            updated = {
                k: v for k, v in existing.items() if k != "id"
            }

            updated["program_contact"] = "graduate-demo@arizona.edu"
            database.save_program(updated, existing["id"])

            return dict(updated, id=existing["id"])

        return existing

    payload = ProgramCreate(
        degree_name=name,
        degree_level=level,
        degree_college=college,
        degree_description=f"Graduate-level studies in {name}.",
        campus_offered=["main", "online"],
        terms_offered=["Fall 2027", "Spring 2028"],
        degree_requirements=(
            "Bachelor's degree and supporting application materials."
        ),
        application_deadline=deadline,
        application_fee="90.00",
        program_contact="graduate-demo@arizona.edu",
    )

    data = payload.model_dump(mode="json")
    program_id = database.save_program(data)

    return dict(data, id=program_id)


def ensure_user(
    username,
    first_name,
    last_name,
    role,
    program_ids=None,
):
    existing = next(
        (
            u for u in database.users()
            if u["username"].casefold() == username.casefold()
        ),
        None,
    )

    if existing:
        if existing["user_type"] != role:
            raise RuntimeError(
                f"Account {username} already has role "
                f"{existing['user_type']}, not {role}."
            )

        updated = {
            k: v for k, v in existing.items() if k != "id"
        }

        changed = False
        old_email = f"{username}@example.test"
        new_email = demo_email(username)

        # Migrate only the old fictional email address.
        if (
            updated.get("email") or ""
        ).casefold() == old_email.casefold():

            conflict = next(
                (
                    u for u in database.users()
                    if u["id"] != existing["id"]
                    and u["email"].casefold() == new_email.casefold()
                ),
                None,
            )

            if conflict:
                raise RuntimeError(
                    f"Cannot migrate {username}: "
                    f"{new_email} is already in use."
                )

            updated["email"] = new_email
            changed = True

        # Restore missing demo program assignments.
        if program_ids is not None:
            assigned = updated.get("assigned_program_ids") or []

            if not assigned:
                updated["assigned_program_ids"] = list(program_ids)
                changed = True

            elif not set(program_ids).issubset(set(assigned)):
                print(
                    f"Warning: {username} has different program "
                    "permissions. Existing permissions were preserved."
                )

        if changed:
            database.save_user(updated, existing["id"])
            return dict(updated, id=existing["id"])

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
        email=demo_email(username),
    )

    created = accounts.register(registration)

    user = next(
        u for u in database.users()
        if u["id"] == created["id"]
    )

    if role != "applicant":
        updated = {
            k: v for k, v in user.items() if k != "id"
        }

        updated["user_type"] = role

        if program_ids is not None:
            updated["assigned_program_ids"] = list(program_ids)

        database.save_user(updated, user["id"])

        return dict(updated, id=user["id"])

    return user


def application_fields(name, email, major, city, gpa="3.65"):
    return {
        "full_name": name,
        "preferred_pronoun": "",
        "date_of_birth": "2002-06-15",
        "mailing_address": f"100 Example Street, {city}, Arizona",
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
        "cumulative_gpa": gpa,

        "reference_1_name": "Dr. Morgan Lee",
        "reference_1_title": "Professor",
        "reference_1_affiliation": "Example State University",
        "reference_1_contact": "demo_reference_morgan@arizona.edu",

        "reference_2_name": "Dr. Taylor Kim",
        "reference_2_title": "Associate Professor",
        "reference_2_affiliation": "Example State University",
        "reference_2_contact": "demo_reference_taylor@arizona.edu",

        "reference_3_name": "Jordan Smith",
        "reference_3_title": "Research Supervisor",
        "reference_3_affiliation": "Example Research Lab",
        "reference_3_contact": "demo_reference_jordan@arizona.edu",

        "sponsor_information": "No current sponsor.",
        "ta_ra_experience": "One year of undergraduate research.",
        "funding_information": "Interested in graduate assistantships.",
        "is_international_applicant": "no",
    }


def update_demo_application_emails(application, user):
    old_email = f"{user['username']}@example.test"
    new_email = user["email"]

    updated = dict(application)
    changed = False

    # Update the email displayed in Reviewer application details.
    if (
        updated.get("email") or ""
    ).casefold() == old_email.casefold():

        updated["email"] = new_email
        changed = True

    fields = updated.get("fields")

    if isinstance(fields, dict):
        fields = dict(fields)

        if (
            fields.get("email_address") or ""
        ).casefold() == old_email.casefold():

            fields["email_address"] = new_email
            changed = True

        reference_emails = {
            "reference_1_contact": (
                "morgan.lee@example.test",
                "demo_reference_morgan@arizona.edu",
            ),
            "reference_2_contact": (
                "taylor.kim@example.test",
                "demo_reference_taylor@arizona.edu",
            ),
            "reference_3_contact": (
                "jordan.smith@example.test",
                "demo_reference_jordan@arizona.edu",
            ),
        }

        for key, (old_address, new_address) in reference_emails.items():
            if (
                fields.get(key) or ""
            ).casefold() == old_address.casefold():

                fields[key] = new_address
                changed = True

        if changed:
            updated["fields"] = fields

    if changed:
        database.save_application(
            updated,
            application["id"],
        )

        saved = database.get_application(application["id"])

        if saved is None:
            raise RuntimeError(
                f"Could not reload application #{application['id']}."
            )

        return saved

    return application


def ensure_application(
    user,
    program,
    status,
    major,
    city,
    term,
    gpa="3.65",
    advisor_id=None,
):
    matches = [
        a for a in database.applications()
        if a["owner_id"] == user["id"]
        and a["program_id"] == program["id"]
    ]

    existing = next(
        (a for a in matches if a.get("term") == term),
        None,
    )

    # Reuse an existing application even if its term was edited.
    if existing is None and len(matches) == 1:
        existing = matches[0]

    elif existing is None and len(matches) > 1:
        raise RuntimeError(
            f"Cannot identify the seed application for "
            f"{user['username']} in {program['degree_name']}. "
            "Multiple records exist."
        )

    if existing is not None:
        return update_demo_application_emails(existing, user)

    payload = ApplicationCreate(
        program_id=program["id"],
        campus="main",
        term=term,
        fields=application_fields(
            f"{user['first_name']} {user['last_name']}",
            user["email"],
            major,
            city,
            gpa,
        ),
        submitted=status != "In Process",
    )

    created = applications.create_application(payload, user)

    if not created or not created.get("id"):
        raise RuntimeError(
            f"Could not create application for {user['username']}."
        )

    application_id = created["id"]

    if status not in {"In Process", "Submitted"}:
        saved = database.get_application(application_id)

        if saved is None:
            raise RuntimeError(
                f"Application #{application_id} was not saved."
            )

        saved["status"] = status

        if status == "In Review":
            saved["review"] = {
                "review_comments": (
                    "Application materials reviewed. "
                    "Ready for committee evaluation."
                ),
                "missing_information": "",
                "reviewer_id": advisor_id,
                "reviewed_at": datetime.now(
                    timezone.utc
                ).isoformat(timespec="seconds"),
            }

        elif status == "Needs Information":
            saved["review"] = {
                "review_comments": (
                    "Additional information is required."
                ),
                "missing_information": (
                    "Please confirm the expected graduation date."
                ),
                "reviewer_id": advisor_id,
                "reviewed_at": datetime.now(
                    timezone.utc
                ).isoformat(timespec="seconds"),
            }

        database.save_application(saved, application_id)

    saved = database.get_application(application_id)

    if saved is None:
        raise RuntimeError(
            f"Could not reload application #{application_id}."
        )

    return saved


def ensure_review_assignment(
    application,
    reviewer,
    advisor,
    due_date,
):
    if application["status"] != "In Review":
        print(
            f"Skipped assignment for #{application['id']}: "
            "not In Review."
        )
        return None

    program_id = application["program_id"]

    if program_id not in (
        reviewer.get("assigned_program_ids") or []
    ):
        print(
            f"Skipped assignment for #{application['id']}: "
            "Reviewer lacks program access."
        )
        return None

    if program_id not in (
        advisor.get("assigned_program_ids") or []
    ):
        print(
            f"Skipped assignment for #{application['id']}: "
            "Advisor lacks program access."
        )
        return None

    existing = next(
        (
            item for item in database.review_assignments()
            if item["application_id"] == application["id"]
            and item["reviewer_id"] == reviewer["id"]
        ),
        None,
    )

    if existing is not None:
        return existing

    return database.save_review_assignment(
        application_id=application["id"],
        reviewer_id=reviewer["id"],
        assigned_by=advisor["id"],
        due_date=due_date.isoformat(),
    )


def main():
    software = ensure_program(
        "Software Engineering",
        "masters",
        "College of Engineering",
        date(2027, 5, 1),
    )

    computer_science = ensure_program(
        "Computer Science",
        "masters",
        "College of Science",
        date(2027, 4, 15),
    )

    # Demo users for all six system roles.
    specs = [
        ("avery", "demo_avery", "Avery", "Bennett", "applicant", None),
        ("maya", "demo_maya", "Maya", "Thompson", "applicant", None),
        ("jordan", "demo_jordan", "Jordan", "Rivera", "applicant", None),
        ("sophia", "demo_sophia", "Sophia", "Martinez", "applicant", None),
        ("liam", "demo_liam", "Liam", "Parker", "applicant", None),
        ("noah", "demo_noah", "Noah", "Walker", "applicant", None),
        ("olivia", "demo_olivia", "Olivia", "Reed", "applicant", None),
        ("ethan", "demo_ethan", "Ethan", "Brooks", "applicant", None),

        ("admin", "demo_admin", "Alex", "Administrator",
         "administrator", None),

        ("advisor_se", "demo_advisor", "Taylor", "Advisor",
         "advisor", [software["id"]]),

        ("advisor_cs", "demo_advisor_cs", "Morgan", "Chen",
         "advisor", [computer_science["id"]]),

        ("reviewer_1", "demo_reviewer_1", "Elena", "Cruz",
         "reviewer", [software["id"]]),

        ("reviewer_2", "demo_reviewer_2", "Daniel", "Hayes",
         "reviewer", [software["id"]]),

        ("reviewer_cs", "demo_reviewer_cs", "Priya", "Shah",
         "reviewer", [computer_science["id"]]),

        ("reference", "demo_reference", "Casey", "Morgan",
         "reference", None),

        ("it_support", "demo_it_support", "Jamie", "Taylor",
         "it_support", None),
    ]

    users = {
        key: ensure_user(
            username,
            first,
            last,
            role,
            program_ids,
        )
        for key, username, first, last, role, program_ids in specs
    }

    # Applications at different stages of processing.
    application_specs = [
        (
            "avery_se", "avery", software, "In Process",
            "Software Engineering", "Tucson", "Fall 2027",
            "3.65", None,
        ),
        (
            "avery_cs", "avery", computer_science, "Submitted",
            "Computer Science", "Tucson", "Spring 2028",
            "3.65", None,
        ),
        (
            "maya_se", "maya", software, "Submitted",
            "Computer Engineering", "Yuma", "Fall 2027",
            "3.65", None,
        ),
        (
            "jordan_cs", "jordan", computer_science, "In Review",
            "Computer Science", "Phoenix", "Fall 2027",
            "3.65", users["advisor_cs"]["id"],
        ),
        (
            "sophia_se", "sophia", software, "In Review",
            "Software Engineering", "Tucson", "Fall 2027",
            "3.88", users["advisor_se"]["id"],
        ),
        (
            "liam_se", "liam", software, "In Review",
            "Information Systems", "Yuma", "Spring 2028",
            "3.42", users["advisor_se"]["id"],
        ),
        (
            "noah_se", "noah", software, "Needs Information",
            "Computer Science", "Tucson", "Fall 2027",
            "3.65", users["advisor_se"]["id"],
        ),
        (
            "olivia_se", "olivia", software, "Accepted",
            "Software Engineering", "Yuma", "Fall 2027",
            "3.65", None,
        ),
        (
            "ethan_cs", "ethan", computer_science, "Denied",
            "Computer Science", "Phoenix", "Fall 2027",
            "3.65", None,
        ),
    ]

    records = {
        key: ensure_application(
            users[user_key],
            prog,
            status,
            major,
            city,
            term,
            gpa,
            advisor_id,
        )
        for (
            key, user_key, prog, status, major,
            city, term, gpa, advisor_id
        ) in application_specs
    }

    deadline = date.today() + timedelta(days=21)

    ensure_review_assignment(
        records["sophia_se"],
        users["reviewer_1"],
        users["advisor_se"],
        deadline,
    )

    ensure_review_assignment(
        records["sophia_se"],
        users["reviewer_2"],
        users["advisor_se"],
        deadline,
    )

    ensure_review_assignment(
        records["jordan_cs"],
        users["reviewer_cs"],
        users["advisor_cs"],
        deadline,
    )

    print("\nUA-GDAS persistent test database ready.")
    print(f"Database: {DEMO_DB}")
    print(f"Password for newly created accounts: {DEMO_PASSWORD}")
    print(
        "Existing passwords, application statuses, "
        "and assignments were preserved."
    )

    print("\nDemo accounts:")
    for user in users.values():
        print(
            f"  {user['username']:<22} "
            f"{user['user_type']:<15} "
            f"{user['email']}"
        )

    print("\nSample applications:")
    for application in records.values():
        print(
            f"  #{application['id']:<3} "
            f"{application['applicant_name']:<18} "
            f"{application['degree_program']:<22} "
            f"{application['status']}"
        )

    print("\nReview assignments:")
    for assignment in database.review_assignments():
        print(
            f"  Application #{assignment['application_id']} -> "
            f"Reviewer #{assignment['reviewer_id']} "
            f"(Due: {assignment['due_date']})"
        )


if __name__ == "__main__":
    main()
