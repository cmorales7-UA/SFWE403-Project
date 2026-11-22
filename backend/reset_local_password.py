"""Interactive password recovery for locally owned UA-GDAS SQLite databases.

Run from the project root:
    python -m backend.reset_local_password --username avery.bennett

This is a local administrative CLI utility. It is not an HTTP endpoint and
does not reveal passwords or modify unrelated user/application records.
"""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import sqlite3

from backend.service.security import hash_secret


DEFAULT_DB = Path(__file__).resolve().parent / "data" / "gdas.sqlite3"


def reset_password(db_path: Path, username: str, password: str) -> int:
    """Reset an existing local account, keeping its user ID and all other data."""
    db_path = db_path.resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    if not 8 <= len(password) <= 256:
        raise ValueError("Password must be between 8 and 256 characters.")

    # Use a transaction and update only the password hash in the JSON record.
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        user = connection.execute(
            "SELECT id, data FROM users WHERE username=? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        if user is None:
            raise LookupError(f"No account found with username: {username}")

        record = json.loads(user["data"])
        record["password_hash"] = hash_secret(password)
        connection.execute(
            "UPDATE users SET data=? WHERE id=?",
            (json.dumps(record), user["id"]),
        )
        # The newly chosen password should take effect with a fresh session.
        connection.execute(
            "DELETE FROM sessions WHERE user_id=?", (user["id"],)
        )
        return user["id"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Reset a local UA-GDAS account password.")
    parser.add_argument(
        "--username", required=True,
        help="Exact login username, e.g. avery.bennett",
    )
    parser.add_argument(
        "--db", type=Path,
        default=Path(os.environ.get("GDAS_DB_PATH", str(DEFAULT_DB))),
        help="SQLite database path (defaults to the local gdas.sqlite3)",
    )
    args = parser.parse_args(argv)
    db_path = args.db.resolve()
    if not db_path.is_file():
        parser.error(f"Database file not found: {db_path}")

    with sqlite3.connect(db_path) as connection:
        try:
            available = connection.execute(
                "SELECT username FROM users ORDER BY username"
            ).fetchall()
        except sqlite3.OperationalError as exc:
            parser.error(f"Could not read account table: {exc}")

    if not any(row[0].casefold() == args.username.casefold() for row in available):
        print(f"Username '{args.username}' does not exist in {db_path}.")
        print("Available usernames:", ", ".join(row[0] for row in available) or "(none)")
        return 1

    print(f"Database: {db_path}")
    print(f"Resetting password for: {args.username}")
    first = getpass("New password (8-256 characters): ")
    second = getpass("Confirm new password: ")
    if first != second:
        print("Passwords did not match. No changes made.")
        return 1

    try:
        reset_password(db_path, args.username, first)
    except (LookupError, ValueError, sqlite3.DatabaseError) as exc:
        print(f"Unable to reset password: {exc}")
        return 1

    print("Password updated. Use the new password to log in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
