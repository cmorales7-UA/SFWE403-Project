"""SRS 9.5.1: persistent program management and administrator/advisor collaboration."""

import json

from fastapi import HTTPException
from backend.clients import database
from backend.service.accounts import require_role


def _can_manage(program, actor):
    if actor["user_type"] == "administrator":
        return True
    return (
        program["id"] in (actor.get("assigned_program_ids") or [])
        or actor["id"] in (program.get("collaborating_advisor_ids") or [])
    )


def list_programs(actor):
    require_role(actor, {"administrator", "advisor"})
    programs = database.programs()
    if actor["user_type"] == "administrator":
        return programs
    return [program for program in programs if _can_manage(program, actor)]


def get_program(program_id, actor):
    program = next(
        (row for row in list_programs(actor) if row["id"] == program_id), None
    )
    if program is None:
        raise HTTPException(404, "Degree program not found")
    return program


def _verify_collaborators(advisor_ids):
    if len(advisor_ids) != len(set(advisor_ids)):
        raise HTTPException(422, "A program advisor may be selected only once")
    advisors = {
        user["id"] for user in database.users()
        if user.get("user_type") == "advisor"
    }
    if any(advisor_id not in advisors for advisor_id in advisor_ids):
        raise HTTPException(422, "Select valid Graduate Degree Advisors")


def _ensure_history_table(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS program_change_history (
            id INTEGER PRIMARY KEY,
            program_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL,
            actor_role TEXT NOT NULL,
            action TEXT NOT NULL CHECK (action IN ('created', 'updated')),
            changed_fields TEXT NOT NULL,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS program_changes_program_idx
        ON program_change_history(program_id)
    """)


def create_program(payload, actor):
    require_role(actor, {"administrator", "advisor"})
    data = payload.model_dump(mode="json")
    if not data["terms_offered"]:
        raise HTTPException(422, "Select at least one application term")
    if data["resident_cost_per_unit"] is None or data["nonresident_cost_per_unit"] is None:
        raise HTTPException(
            422, "Enter both Arizona resident and non-resident tuition per unit"
        )

    if actor["user_type"] == "administrator":
        _verify_collaborators(data["collaborating_advisor_ids"])
    else:
        # An advisor participating in creation is automatically listed.
        data["collaborating_advisor_ids"] = [actor["id"]]

    # Program creation, advisor access and audit history commit together.
    with database.connect() as connection:
        _ensure_history_table(connection)
        cursor = connection.execute(
            "INSERT INTO programs(data) VALUES (?)",
            (json.dumps(data),),
        )
        program_id = cursor.lastrowid

        if actor["user_type"] == "advisor":
            saved_user = connection.execute(
                "SELECT data FROM users WHERE id=?", (actor["id"],)
            ).fetchone()
            if saved_user is None:
                raise HTTPException(404, "Advisor account not found")
            account = json.loads(saved_user["data"])
            programs = set(account.get("assigned_program_ids") or [])
            programs.add(program_id)
            account["assigned_program_ids"] = sorted(programs)
            connection.execute(
                "UPDATE users SET data=? WHERE id=?",
                (json.dumps(account), actor["id"]),
            )

        connection.execute(
            """INSERT INTO program_change_history
               (program_id, actor_id, actor_role, action, changed_fields)
               VALUES (?, ?, ?, 'created', ?)""",
            (program_id, actor["id"], actor["user_type"],
             json.dumps(sorted(data))),
        )

    return dict(data, id=program_id)


def update_program(program_id, payload, actor):
    require_role(actor, {"administrator", "advisor"})
    previous = get_program(program_id, actor)
    data = payload.model_dump(mode="json")

    if actor["user_type"] == "administrator":
        if "collaborating_advisor_ids" not in payload.model_fields_set:
            data["collaborating_advisor_ids"] = previous.get(
                "collaborating_advisor_ids", []
            )
        _verify_collaborators(data["collaborating_advisor_ids"])
    else:
        # Advisors may contribute to program details but cannot grant access.
        data["collaborating_advisor_ids"] = previous.get(
            "collaborating_advisor_ids", []
        )

    # Older program clients must not silently wipe established fields.
    for field in (
        "resident_cost_per_unit", "nonresident_cost_per_unit", "custom_questions",
    ):
        if field not in payload.model_fields_set:
            data[field] = previous.get(field, [] if field == "custom_questions" else None)
    if not data["terms_offered"]:
        raise HTTPException(422, "Select at least one application term")

    changed_fields = sorted(
        name for name in set(previous) | set(data)
        if name != "id" and previous.get(name) != data.get(name)
    )
    if not changed_fields:
        return dict(data, id=program_id)

    with database.connect() as connection:
        _ensure_history_table(connection)
        cursor = connection.execute(
            "UPDATE programs SET data=? WHERE id=?",
            (json.dumps(data), program_id),
        )
        if cursor.rowcount != 1:
            raise HTTPException(404, "Degree program not found")
        connection.execute(
            """INSERT INTO program_change_history
               (program_id, actor_id, actor_role, action, changed_fields)
               VALUES (?, ?, ?, 'updated', ?)""",
            (program_id, actor["id"], actor["user_type"],
             json.dumps(changed_fields)),
        )

    return dict(data, id=program_id)


def change_history(program_id, actor):
    get_program(program_id, actor)
    with database.connect() as connection:
        _ensure_history_table(connection)
        rows = connection.execute(
            """SELECT actor_id, actor_role, action, changed_fields, changed_at
               FROM program_change_history WHERE program_id=?
               ORDER BY id DESC""",
            (program_id,),
        ).fetchall()
    users = {user["id"]: user for user in database.users()}
    history = []
    for item in rows:
        actor_user = users.get(item["actor_id"]) or {}
        full_name = " ".join(
            part for part in (
                actor_user.get("first_name", ""),
                actor_user.get("last_name", ""),
            ) if part
        ) or f"User #{item['actor_id']}"
        history.append({
            "actor_name": full_name,
            "actor_role": item["actor_role"],
            "action": item["action"],
            "changed_fields": json.loads(item["changed_fields"]),
            "changed_at": item["changed_at"],
        })
    return history
