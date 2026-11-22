"""One-time data setup and conservative legacy account migration."""
import os
import shutil
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


def prepare():
    target = Path(os.environ.get("GDAS_DB_PATH", str(DEFAULT_DB))).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    os.environ["GDAS_DB_PATH"] = str(target)

    if not target.exists():
        if LEGACY_DB.exists() and target != LEGACY_DB.resolve():
            # Copy instead of deleting or modifying the previous DB.
            shutil.copy2(LEGACY_DB, target)
            print("Previously saved applications and accounts were retained.")
        else:
            initialize_first_run()

    upgrade_existing_accounts()


if __name__ == "__main__":
    prepare()
