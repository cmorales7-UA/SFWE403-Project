"""One-time data setup and conservative legacy account migration."""
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from backend.clients import database
from backend.initial_data import main as initialize_first_run


DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_DB = DATA_DIR / "gdas.sqlite3"
LEGACY_DB = DATA_DIR / "mvp1_demo.sqlite3"

# Only these original, known starter accounts may be renamed.
ACCOUNT_NAMES = {
    "demo_avery": "avery.bennett",
    "demo_maya": "maya.thompson",
    "demo_jordan": "jordan.rivera",
    "demo_sophia": "sophia.martinez",
    "demo_liam": "liam.parker",
    "demo_noah": "noah.walker",
    "demo_olivia": "olivia.reed",
    "demo_ethan": "ethan.brooks",
    "demo_admin": "alex.morgan",
    "demo_advisor": "taylor.bennett",
    "demo_advisor_cs": "morgan.chen",
    "demo_reviewer_1": "elena.cruz",
    "demo_reviewer_2": "daniel.hayes",
    "demo_reviewer_cs": "priya.shah",
    "demo_reference": "casey.morgan",
    "demo_it_support": "jamie.taylor",
}


def upgrade_existing_accounts():
    current = database.users()
    usernames = {account["username"].casefold(): account["id"] for account in current}
    emails = {account["email"].casefold(): account["id"] for account in current}

    for account in current:
        old_username = account["username"]
        new_username = ACCOUNT_NAMES.get(old_username.casefold())
        if not new_username:
            continue

        old_email = account["email"]
        new_email = f"{new_username}@arizona.edu"

        # Renaming is limited to the original seeded account addresses. Any
        # independently edited email address remains unchanged.
        expected_emails = {
            f"{old_username}@arizona.edu".casefold(),
            f"{old_username}@example.test".casefold(),
        }
        change_email = old_email.casefold() in expected_emails

        if new_username in usernames and usernames[new_username] != account["id"]:
            print(f"Skipped conflicting username for account #{account['id']}.")
            continue
        if change_email and new_email.casefold() in emails and emails[new_email.casefold()] != account["id"]:
            print(f"Skipped conflicting email for account #{account['id']}.")
            continue

        original_id = account.pop("id")
        account["username"] = new_username
        if change_email:
            account["email"] = new_email

        if old_username == "demo_admin" and account.get("last_name") == "Administrator":
            account["last_name"] = "Morgan"
        if old_username == "demo_advisor" and account.get("last_name") == "Advisor":
            account["last_name"] = "Bennett"
        if not account.get("net_id"):
            account["net_id"] = new_username.replace(".", "")

        database.save_user(account, original_id)

        if change_email:
            with database.connect() as connection:
                # Historical reference requests must follow the renamed recipient.
                connection.execute(
                    """UPDATE recommendation_requests
                       SET recipient_email=? WHERE LOWER(recipient_email)=LOWER(?)""",
                    (new_email, old_email),
                )

            # Update only original embedded addresses belonging to this owner.
            for application in database.applications():
                if application["owner_id"] != original_id:
                    continue
                changed = False
                if application.get("email", "").casefold() == old_email.casefold():
                    application["email"] = new_email
                    changed = True
                fields = application.get("fields") or {}
                if fields.get("email_address", "").casefold() == old_email.casefold():
                    fields["email_address"] = new_email
                    changed = True
                if changed:
                    database.save_application(application, application["id"])

    # Remove outdated contact labels only when they exactly match the
    # original starter values; retain any manually edited contacts.
    for program in database.programs():
        if program.get("program_contact") in {
            "graduate-demo@arizona.edu", "graduate@example.test",
        }:
            program["program_contact"] = "gdas.programs@arizona.edu"
            identifier = program.pop("id")
            database.save_program(program, identifier)

    previous_references = {
        "demo_reference_morgan@arizona.edu": "morgan.lee@arizona.edu",
        "demo_reference_taylor@arizona.edu": "taylor.kim@arizona.edu",
        "demo_reference_jordan@arizona.edu": "jordan.smith@arizona.edu",
    }
    for application in database.applications():
        fields = application.get("fields") or {}
        modified = False
        for key in ("reference_1_contact", "reference_2_contact", "reference_3_contact"):
            former = str(fields.get(key) or "").casefold()
            if former in previous_references:
                fields[key] = previous_references[former]
                modified = True
        if modified:
            database.save_application(application, application["id"])



def _read_only_connection(path: Path):
    """Open an existing database without accidentally creating a new file."""
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _user_count(path: Path) -> int:
    if not path.is_file():
        return 0
    with closing(_read_only_connection(path)) as connection:
        try:
            return int(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        except sqlite3.OperationalError as error:
            if "no such table" in str(error).lower():
                return 0
            raise


def _contains_other_data(path: Path) -> bool:
    """Preserve databases with applications, programs, reviews, or any records."""
    with closing(_read_only_connection(path)) as connection:
        tables = [
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for table in tables:
            # SQLite table names from sqlite_master, not user-supplied input.
            safe_table = '"' + table.replace('"', '""') + '"'
            if connection.execute(
                f"SELECT 1 FROM {safe_table} LIMIT 1"
            ).fetchone():
                return True
    return False


def _backup_empty_file(path: Path) -> Path:
    """Keep the original empty database on disk when recovering a previous DB."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.stem}.before-recovery.{stamp}{path.suffix}")
    count = 1
    while backup.exists():
        backup = path.with_name(
            f"{path.stem}.before-recovery.{stamp}.{count}{path.suffix}"
        )
        count += 1
    shutil.copy2(path, backup)
    print(f"Preserved previous database file: {backup}")
    return backup



def prepare():
    target = Path(os.environ.get("GDAS_DB_PATH", str(DEFAULT_DB))).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    os.environ["GDAS_DB_PATH"] = str(target)

    # Checking file existence alone is not sufficient: opening SQLite for a
    # read can create an empty gdas.sqlite3. Check for persisted users.
    if _user_count(target) == 0:
        if target.exists() and _contains_other_data(target):
            raise SystemExit(
                "The selected database contains saved records but no user "
                "accounts. Nothing was replaced. Inspect the database before "
                "continuing to avoid orphaning applications or reviews."
            )

        has_legacy_users = (
            LEGACY_DB.resolve() != target
            and _user_count(LEGACY_DB) > 0
        )

        if has_legacy_users:
            if target.exists():
                # Preserve rather than delete the empty/newer file.
                _backup_empty_file(target)
            shutil.copy2(LEGACY_DB, target)
            print("Recovered existing UA-GDAS accounts and applications.")
            print(f"Source: {LEGACY_DB}")
        else:
            print("No saved accounts found. Initializing new local accounts.")
            initialize_first_run()

    upgrade_existing_accounts()
    print(f"Active database: {target}")
    print(f"Registered accounts: {len(database.users())}")


if __name__ == "__main__":
    prepare()
