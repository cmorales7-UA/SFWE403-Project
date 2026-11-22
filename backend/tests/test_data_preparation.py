"""Check first-run identity setup and non-destructive migration."""

from backend.clients import database
from backend import prepare_data


def test_known_existing_account_ids_and_password_hashes_are_preserved(
    tmp_path, monkeypatch,
):
    path = tmp_path / "existing.sqlite3"
    monkeypatch.setenv("GDAS_DB_PATH", str(path))

    account_id = database.save_user({
        "username": "demo_admin",
        "email": "demo_admin@arizona.edu",
        "first_name": "Alex",
        "last_name": "Administrator",
        "user_type": "administrator",
        "password_hash": "unchanged-hash",
        "assigned_program_ids": [],
    })
    program_id = database.save_program({
        "degree_name": "Software Engineering",
        "program_contact": "graduate-demo@arizona.edu",
    })
    application_id = database.save_application({
        "owner_id": account_id,
        "program_id": program_id,
        "applicant_name": "Alex Administrator",
        "email": "demo_admin@arizona.edu",
        "status": "In Review",
        "fields": {"email_address": "demo_admin@arizona.edu"},
        "review": {"reviewed_at": "2026-11-20"},
    })

    prepare_data.prepare()
    user = database.users()[0]
    assert user["id"] == account_id
    assert user["username"] == "alex.morgan"
    assert user["email"] == "alex.morgan@arizona.edu"
    assert user["last_name"] == "Morgan"
    assert user["password_hash"] == "unchanged-hash"

    saved = database.get_application(application_id)
    assert saved["owner_id"] == account_id
    assert saved["status"] == "In Review"
    assert saved["review"]["reviewed_at"] == "2026-11-20"
    assert saved["email"] == "alex.morgan@arizona.edu"
    assert saved["fields"]["email_address"] == "alex.morgan@arizona.edu"
    assert database.programs()[0]["program_contact"] == "gdas.programs@arizona.edu"

    # Restarting setup does not duplicate or overwrite anything.
    prepare_data.prepare()
    assert len(database.users()) == 1
    assert len(database.programs()) == 1
    assert len(database.applications()) == 1


def test_initial_accounts_have_full_names_and_arizona_email_addresses(
    tmp_path, monkeypatch,
):
    path = tmp_path / "fresh.sqlite3"
    monkeypatch.setenv("GDAS_DB_PATH", str(path))
    monkeypatch.setenv("GDAS_STARTER_PASSWORD", "TemporaryLocal123!")
    prepare_data.prepare()
    people = database.users()
    assert len(people) >= 10
    assert all(user["first_name"] and user["last_name"] for user in people)
    assert all(user["email"].endswith("@arizona.edu") for user in people)
    assert all(not user["username"].startswith("demo_") for user in people)
    assert any(user["user_type"] == "administrator" for user in people)
    assert database.applications()

    count = len(database.applications())
    prepare_data.prepare()
    assert len(database.applications()) == count
