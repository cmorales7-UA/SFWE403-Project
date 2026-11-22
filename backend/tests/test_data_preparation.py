"""Check first-run identity setup and non-destructive migration."""

import sqlite3
from pathlib import Path

import pytest

from backend.clients import database
from backend import prepare_data


def test_known_existing_account_ids_and_password_hashes_are_preserved(
    tmp_path, monkeypatch,
):
    path = tmp_path / "existing.sqlite3"
    monkeypatch.setenv("GDAS_DB_PATH", str(path))
    monkeypatch.setattr(prepare_data, "LEGACY_DB", tmp_path / "none.sqlite3")

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
    monkeypatch.setattr(prepare_data, "LEGACY_DB", tmp_path / "none.sqlite3")
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


def test_existing_empty_new_database_recovers_legacy_without_losing_records(
    tmp_path, monkeypatch,
):
    legacy = tmp_path / "mvp1_demo.sqlite3"
    primary = tmp_path / "gdas.sqlite3"
    monkeypatch.setattr(prepare_data, "LEGACY_DB", legacy)

    # Set up an actual historical account and application.
    monkeypatch.setenv("GDAS_DB_PATH", str(legacy))
    user_id = database.save_user({
        "username": "demo_avery",
        "email": "demo_avery@arizona.edu",
        "first_name": "Avery",
        "last_name": "Bennett",
        "password_hash": "original-hash",
        "user_type": "applicant",
        "assigned_program_ids": [],
    })
    program_id = database.save_program({"degree_name": "Software Engineering"})
    application_id = database.save_application({
        "owner_id": user_id,
        "program_id": program_id,
        "applicant_name": "Avery Bennett",
        "email": "demo_avery@arizona.edu",
        "status": "In Review",
        "fields": {"email_address": "demo_avery@arizona.edu"},
        "review": {"reviewed_at": "2026-11-21"},
    })

    # The bug: merely looking up accounts creates an empty SQLite file.
    monkeypatch.setenv("GDAS_DB_PATH", str(primary))
    assert database.users() == []
    assert primary.exists()

    prepare_data.prepare()
    restored = database.users()
    assert len(restored) == 1
    assert restored[0]["id"] == user_id
    assert restored[0]["username"] == "avery.bennett"
    assert restored[0]["password_hash"] == "original-hash"
    assert database.get_application(application_id)["review"]["reviewed_at"] == "2026-11-21"
    assert len(list(tmp_path.glob("gdas.before-recovery.*.sqlite3"))) == 1

    prepare_data.prepare()
    assert len(database.users()) == 1
    assert len(database.applications()) == 1


def test_existing_empty_database_initializes_without_legacy_users(
    tmp_path, monkeypatch,
):
    target = tmp_path / "gdas.sqlite3"
    monkeypatch.setenv("GDAS_DB_PATH", str(target))
    monkeypatch.setattr(prepare_data, "LEGACY_DB", tmp_path / "no-legacy.sqlite3")
    monkeypatch.setenv("GDAS_STARTER_PASSWORD", "TemporaryLocal123!")

    # Create a legitimate SQLite file and schema with no actual records.
    assert database.users() == []
    assert target.exists()
    prepare_data.prepare()
    assert len(database.users()) >= 10
    assert database.applications()


def test_program_data_without_users_is_not_overwritten(
    tmp_path, monkeypatch,
):
    target = tmp_path / "gdas.sqlite3"
    legacy = tmp_path / "mvp1_demo.sqlite3"
    monkeypatch.setattr(prepare_data, "LEGACY_DB", legacy)
    monkeypatch.setenv("GDAS_DB_PATH", str(target))
    program_id = database.save_program({
        "degree_name": "Previously Saved Degree",
        "degree_level": "masters",
    })
    assert database.users() == []

    with pytest.raises(SystemExit, match="contains saved records"):
        prepare_data.prepare()
    assert database.programs()[0]["id"] == program_id
    assert database.programs()[0]["degree_name"] == "Previously Saved Degree"
    assert database.users() == []
