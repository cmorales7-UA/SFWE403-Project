"""Verify interactive local password recovery preserves all unrelated records."""

from pathlib import Path
import sqlite3

import pytest

from backend.clients import database
from backend.reset_local_password import reset_password, main
from backend.service.security import hash_secret, verify_secret


def test_password_reset_changes_only_target_account_and_invalidates_sessions(tmp_path, monkeypatch):
    db_path = tmp_path / "gdas.sqlite3"
    monkeypatch.setenv("GDAS_DB_PATH", str(db_path))
    original = {
        "username": "avery.bennett",
        "email": "avery.bennett@arizona.edu",
        "first_name": "Avery",
        "last_name": "Bennett",
        "user_type": "applicant",
        "password_hash": hash_secret("OldPassword123!"),
        "assigned_program_ids": [],
    }
    user_id = database.save_user(original)
    other_id = database.save_user({
        **original, "username": "alex.morgan",
        "email": "alex.morgan@arizona.edu",
        "user_type": "administrator",
    })
    program_id = database.save_program({"degree_name": "Software Engineering"})
    application_id = database.save_application({
        "owner_id": user_id,
        "program_id": program_id,
        "applicant_name": "Avery Bennett",
        "status": "Submitted",
        "fields": {"statement": "Keep this draft"},
    })
    with database.connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires) VALUES (?, ?, ?)",
            ("older-session", user_id, 9999999999),
        )

    result = reset_password(db_path, "avery.bennett", "NewPassword456!")
    assert result == user_id
    updated = next(user for user in database.users() if user["id"] == user_id)
    other = next(user for user in database.users() if user["id"] == other_id)

    assert verify_secret("NewPassword456!", updated["password_hash"])
    assert not verify_secret("OldPassword123!", updated["password_hash"])
    for key in ("username", "email", "first_name", "last_name", "user_type"):
        assert updated[key] == original[key]
    assert other["password_hash"] == original["password_hash"]
    assert database.get_application(application_id)["fields"]["statement"] == "Keep this draft"
    assert database.get_application(application_id)["status"] == "Submitted"
    with database.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE user_id=?", (user_id,)
        ).fetchone()[0] == 0


def test_no_existing_user_or_database_is_modified(tmp_path, monkeypatch):
    db_path = tmp_path / "gdas.sqlite3"
    monkeypatch.setenv("GDAS_DB_PATH", str(db_path))
    assert not db_path.exists()
    with pytest.raises(FileNotFoundError):
        reset_password(db_path, "avery.bennett", "NewPassword456!")
    assert not db_path.exists()

    user_id = database.save_user({
        "username": "avery.bennett",
        "email": "avery.bennett@arizona.edu",
        "user_type": "applicant",
        "password_hash": hash_secret("OldPassword123!"),
    })
    with pytest.raises(LookupError):
        reset_password(db_path, "wrong.user", "NewPassword456!")
    with pytest.raises(ValueError):
        reset_password(db_path, "avery.bennett", "short")

    unchanged = next(u for u in database.users() if u["id"] == user_id)
    assert verify_secret("OldPassword123!", unchanged["password_hash"])


def test_interactive_cli_accepts_confirmed_password(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "gdas.sqlite3"
    monkeypatch.setenv("GDAS_DB_PATH", str(db_path))
    user_id = database.save_user({
        "username": "avery.bennett",
        "email": "avery.bennett@arizona.edu",
        "user_type": "applicant",
        "password_hash": hash_secret("OldPassword123!"),
    })
    import backend.reset_local_password as command
    input_values = iter(["NewPassword456!", "NewPassword456!"])
    monkeypatch.setattr(command, "getpass", lambda prompt: next(input_values))
    assert main(["--username", "avery.bennett", "--db", str(db_path)]) == 0
    output = capsys.readouterr().out
    assert "Password updated" in output
    assert "NewPassword456!" not in output
    account = next(u for u in database.users() if u["id"] == user_id)
    assert verify_secret("NewPassword456!", account["password_hash"])
