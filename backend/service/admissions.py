"""SRS 9.5.2–9.5.5: official admission, enrollment intent, student records.

Only the registered applicant can submit their intent through the portal.
Graduate College administrators alone issue formal notices and process intent.
The Registrar notification is deliberately local and never calls an outside API.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets

from fastapi import HTTPException

from backend.clients import database
from backend.service import accounts, graduate_college, mailer


FINAL_OUTCOMES = {"Recommend": "Accepted", "Deny": "Denied"}
TUITION_OPTIONS = {"resident", "nonresident"}
MAX_TRANSCRIPT_BYTES = 10 * 1024 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _make_tables(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS official_admission_notices (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL UNIQUE,
            decision_version INTEGER NOT NULL,
            administrator_id INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK (decision IN ('Accepted', 'Denied')),
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            email_body TEXT NOT NULL,
            letter_body TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('prepared','sent','failed')),
            prepared_at TEXT NOT NULL,
            sent_at TEXT
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS admission_intents (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL UNIQUE,
            applicant_id INTEGER NOT NULL,
            channel TEXT NOT NULL,
            received_at TEXT NOT NULL,
            processed_at TEXT,
            processed_by INTEGER
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS official_transcripts (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            storage_name TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            verified_by INTEGER NOT NULL,
            received_at TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS admitted_graduate_students (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL UNIQUE,
            student_account_id INTEGER NOT NULL,
            record_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS registrar_simulations (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL UNIQUE,
            student_record_id INTEGER,
            term TEXT NOT NULL,
            notice_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)


def _application(application_id):
    application = database.get_application(application_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    return application


def _get_row(connection, table, application_id):
    return connection.execute(
        f"SELECT * FROM {table} WHERE application_id=?",
        (application_id,),
    ).fetchone()


def summary(application_id, actor):
    accounts.require_role(actor, {"administrator", "applicant"})
    application = _application(application_id)
    if actor["user_type"] == "applicant" and application["owner_id"] != actor["id"]:
        raise HTTPException(403, "You cannot access another applicant's records")

    with database.connect() as db:
        _make_tables(db)
        notice = _get_row(db, "official_admission_notices", application_id)
        intent = _get_row(db, "admission_intents", application_id)
        student = _get_row(db, "admitted_graduate_students", application_id)
        registrar = _get_row(db, "registrar_simulations", application_id)
        transcript = _get_row(db, "official_transcripts", application_id)

    result = {
        "application_id": application_id,
        "application_status": application["status"],
        "notice": {
            "decision": notice["decision"],
            "state": notice["state"],
            "sent_at": notice["sent_at"],
        } if notice else None,
        "intent": {
            "received_at": intent["received_at"],
            "processed_at": intent["processed_at"],
            "channel": intent["channel"],
        } if intent else None,
    }
    if actor["user_type"] == "administrator":
        result.update({
            "student_record_id": student["id"] if student else None,
            "registrar_notification_at": registrar["created_at"] if registrar else None,
            "transcript": {
                "filename": transcript["filename"],
                "verified_by": transcript["verified_by"],
                "received_at": transcript["received_at"],
            } if transcript else None,
        })
    return result


def list_cases(actor):
    accounts.require_role(actor, {"administrator"})
    cases = []
    for application in database.applications():
        recommendation = graduate_college.get_saved_decision(application["id"])
        state = summary(application["id"], actor)
        notified_version = False
        if recommendation:
            notified_version = any(
                notification["administrator_id"] == actor["id"]
                and notification["decision_version"] == recommendation["version"]
                for notification in graduate_college.get_notifications(application["id"])
            )
        cases.append({
            "id": application["id"],
            "applicant_name": application.get("applicant_name") or application.get("full_name"),
            "email": application.get("email", ""),
            "degree_program": application.get("degree_program", ""),
            "term": application.get("term", ""),
            "campus": application.get("campus", ""),
            "status": application.get("status", ""),
            "recommendation": recommendation["decision"] if recommendation else None,
            "recommendation_received": notified_version,
            **state,
        })
    return cases


def _ready_to_notify(application, actor):
    if application.get("status") != "In Review":
        raise HTTPException(409, "Only reviewed applications awaiting a final decision qualify")

    saved = graduate_college.get_saved_decision(application["id"])
    if not saved or saved["decision"] not in FINAL_OUTCOMES:
        raise HTTPException(409, "A final Recommend or Deny decision from the advisor is required")
    received = any(
        item["administrator_id"] == actor["id"]
        and item["decision_version"] == saved["version"]
        for item in graduate_college.get_notifications(application["id"])
    )
    if not received:
        raise HTTPException(409, "This Graduate College Administrator must first receive the advisor's decision")
    return saved


def _formal_letter(application, program, decision):
    action = (
        "The Graduate College is pleased to inform you that your application "
        "has been accepted for admission."
        if decision == "Accepted"
        else "The Graduate College regrets to inform you that your "
             "application has not been accepted for admission."
    )
    lines = [
        "THE UNIVERSITY OF ARIZONA",
        "GRADUATE COLLEGE",
        "Graduate Admission Decision",
        "",
        f"Date: {_now()[:10]}",
        f"To: {application.get('applicant_name', 'Applicant')}",
        f"Mailing address: {(application.get('fields') or {}).get('mailing_address') or 'Address not provided'}",
        "",
        f"Dear {application.get('applicant_name', 'Applicant')},",
        "",
        action,
        "",
        f"Graduate degree program: {program.get('degree_name') or application.get('degree_program')}",
        f"Degree level: {program.get('degree_level', 'Not specified')}",
        f"Administering college: {program.get('degree_college', 'Not specified')}",
        f"Campus: {application.get('campus', 'Not specified')}",
        f"Academic term: {application.get('term', 'Not specified')}",
        f"Program contact: {program.get('program_contact', 'Not specified')}",
        "",
    ]
    if decision == "Accepted":
        lines.extend([
            "Please use UA-GDAS to notify the Graduate College if you intend",
            "to accept this offer. Submitting your intent does not itself",
            "complete Graduate College enrollment processing.",
            "",
        ])
    lines.extend([
        "Sincerely,",
        "Graduate College Admissions",
        "UA-GDAS",
        "",
        "Course-project correspondence. Not a verified university admission letter.",
    ])
    return "\n".join(lines)


def issue_official_notice(application_id, actor):
    accounts.require_role(actor, {"administrator"})
    application = _application(application_id)
    decision = _ready_to_notify(application, actor)
    outcome = FINAL_OUTCOMES[decision["decision"]]
    program = next(
        (record for record in database.programs() if record["id"] == application["program_id"]),
        None,
    )
    if program is None:
        raise HTTPException(409, "Degree program record is missing")

    if not application.get("email") or "@" not in application["email"]:
        raise HTTPException(422, "Applicant email address is missing or invalid")

    with database.connect() as db:
        _make_tables(db)
        existing = _get_row(db, "official_admission_notices", application_id)
        if existing:
            if existing["state"] == "sent":
                raise HTTPException(409, "The official decision has already been sent")
            if existing["state"] == "prepared":
                raise HTTPException(409, "A notice is already prepared; reconcile delivery before retrying")
            if existing["decision_version"] != decision["version"]:
                raise HTTPException(409, "A newer advisor decision requires administrative review")

        letter = _formal_letter(application, program, outcome)
        subject = f"UA-GDAS Graduate College Admission Decision: {outcome}"
        body = (
            "Graduate College admission decision\n\n"
            + letter
            + "\n\nThe printable copy is available to the Graduate College Administrator.\n"
        )
        if existing is None:
            db.execute(
                """INSERT INTO official_admission_notices
                   (application_id, decision_version, administrator_id, decision,
                    recipient_email, subject, email_body, letter_body,
                    state, prepared_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'prepared', ?)""",
                (application_id, decision["version"], actor["id"], outcome,
                 application["email"], subject, body, letter, _now()),
            )
        else:
            db.execute(
                """UPDATE official_admission_notices
                   SET state='prepared', administrator_id=?, prepared_at=?
                   WHERE application_id=?""",
                (actor["id"], _now(), application_id),
            )

    # SMTP acceptance is required; never simulate a successful email send.
    try:
        mailer.send_email(application["email"], subject, body)
    except Exception:
        with database.connect() as db:
            _make_tables(db)
            db.execute(
                """UPDATE official_admission_notices SET state='failed'
                   WHERE application_id=? AND state='prepared'""",
                (application_id,),
            )
        raise

    # Persist delivery result and formal status together.
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _make_tables(db)
        record = _get_row(db, "official_admission_notices", application_id)
        if record["state"] != "prepared":
            raise HTTPException(409, "Notice state changed while sending")
        application["status"] = outcome
        application["last_updated"] = _now()
        application["official_decision_date"] = _now()
        application["advisor_decision_version"] = decision["version"]
        document = dict(application)
        document.pop("id", None)
        db.execute(
            "UPDATE applications SET data=? WHERE id=?",
            (json.dumps(document), application_id),
        )
        db.execute(
            """UPDATE official_admission_notices
               SET state='sent', sent_at=? WHERE application_id=?""",
            (_now(), application_id),
        )
    return summary(application_id, actor)


def notify_acceptance(application_id, actor):
    accounts.require_role(actor, {"applicant"})
    application = _application(application_id)
    if application["owner_id"] != actor["id"]:
        raise HTTPException(403, "Only the applicant may notify acceptance")
    if application["status"] != "Accepted":
        raise HTTPException(409, "An accepted formal admission offer is required")
    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _make_tables(db)
        notice = _get_row(db, "official_admission_notices", application_id)
        if notice is None or notice["state"] != "sent" or notice["decision"] != "Accepted":
            raise HTTPException(409, "The official acceptance notification must be sent first")
        if _get_row(db, "admission_intents", application_id):
            raise HTTPException(409, "The Graduate College has already received your intent")
        db.execute(
            """INSERT INTO admission_intents
               (application_id, applicant_id, channel, received_at)
               VALUES (?, ?, 'applicant_portal', ?)""",
            (application_id, actor["id"], _now()),
        )
    return summary(application_id, actor)


def _student_snapshot(application, account, program, classification, transcript):
    fields = application.get("fields") or {}
    education = {
        "institution": fields.get("university_name") or None,
        "education_degree_name": fields.get("education_degree_name") or None,
        "degree_type": fields.get("degree_type") or None,
        "degree_name": fields.get("degree_name") or None,
        "degree_start_date": fields.get("degree_start_date") or None,
        "degree_received_date": fields.get("degree_received_date") or None,
        "total_credits": fields.get("total_credits") or None,
        "cumulative_gpa": fields.get("cumulative_gpa") or None,
    }
    tuition_field = (
        "resident_cost_per_unit" if classification == "resident"
        else "nonresident_cost_per_unit"
    )
    tuition = program.get(tuition_field)
    if tuition in (None, ""):
        raise HTTPException(
            409, "Set the approved per-unit tuition rate in Degree Program Management before processing"
        )
    # The applicant's self-reported residency field is preserved separately.
    # The administrator's explicit classification determines the rate selected.
    record = {
        "application_id": application["id"],
        "account_id": account["id"],
        "full_name": application.get("full_name") or application.get("applicant_name"),
        "preferred_pronoun": fields.get("preferred_pronoun") or None,
        "date_of_birth": fields.get("date_of_birth") or None,
        "net_id": account.get("net_id") or None,
        "email": account.get("email") or application.get("email"),
        "phone": fields.get("phone") or account.get("phone") or None,
        "mailing_address": fields.get("mailing_address") or None,
        "citizenship": fields.get("citizenship") or None,
        "country_of_birth": fields.get("country_of_birth") or None,
        "legal_residence_country": fields.get("legal_residence_country") or None,
        "visa": fields.get("visa") or None,
        "military_affiliation": fields.get("military_affiliation") or None,
        "previous_ua_affiliation": fields.get("previous_ua_affiliation") or None,
        "resident_tuition_eligibility_reported": fields.get("resident_tuition_eligibility") or None,
        "tuition_classification": classification,
        "tuition_amount_per_unit": str(tuition),
        "tuition_currency": "USD",
        "graduate_degree_program": program["degree_name"],
        "degree_level": program.get("degree_level"),
        "college": program.get("degree_college"),
        "campus": application.get("campus"),
        "term": application.get("term"),
        "education_history": [education],
        "cumulative_gpa": education["cumulative_gpa"],
        "official_transcripts": {
            "status": "Verified copy on file" if transcript else "Not on file",
            "document_id": transcript["id"] if transcript else None,
            "filename": transcript["filename"] if transcript else None,
            "sha256": transcript["sha256"] if transcript else None,
        },
        "ethnicity": fields.get("ethnicity") or None,
    }
    mandatory = [
        "full_name", "net_id", "email", "phone", "mailing_address",
        "date_of_birth", "citizenship", "country_of_birth",
        "legal_residence_country", "resident_tuition_eligibility_reported",
        "military_affiliation", "cumulative_gpa", "ethnicity",
    ]
    missing = [name for name in mandatory if not record.get(name)]
    if not transcript:
        missing.append("official_transcripts")
    for field in (
        "institution", "education_degree_name", "degree_type", "degree_name",
        "total_credits", "degree_start_date", "degree_received_date",
    ):
        if not education[field]:
            missing.append(f"education_history.{field}")
    record["missing_verification_fields"] = missing
    return record


def create_student_record(application_id, actor, classification):
    """SRS 9.5.5: create an admitted student record after a formal acceptance.

    This is independent of applicant enrollment intent (SRS 9.5.3).
    Require an actual verified transcript and source application fields.
    """
    accounts.require_role(actor, {"administrator"})
    if classification not in TUITION_OPTIONS:
        raise HTTPException(422, "Select a resident or non-resident tuition classification")
    application = _application(application_id)
    if application["status"] not in {"Accepted", "Intent to Matriculate"}:
        raise HTTPException(409, "A formal acceptance is required before creating a student record")
    account = next((u for u in database.users() if u["id"] == application["owner_id"]), None)
    program = next((p for p in database.programs() if p["id"] == application["program_id"]), None)
    if account is None or program is None:
        raise HTTPException(409, "Applicant account or program record is missing")

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _make_tables(db)
        notice = _get_row(db, "official_admission_notices", application_id)
        if notice is None or notice["state"] != "sent" or notice["decision"] != "Accepted":
            raise HTTPException(409, "An official acceptance email must be delivered first")
        if _get_row(db, "admitted_graduate_students", application_id):
            raise HTTPException(409, "An admitted student record already exists")

        transcript = _get_row(db, "official_transcripts", application_id)
        snapshot = _student_snapshot(application, account, program, classification, transcript)
        if snapshot["missing_verification_fields"]:
            raise HTTPException(
                422,
                "Complete missing ConOps record requirements before creating a student record: "
                + ", ".join(snapshot["missing_verification_fields"]),
            )
        timestamp = _now()
        snapshot["record_created_at"] = timestamp
        cursor = db.execute(
            """INSERT INTO admitted_graduate_students
               (application_id, student_account_id, record_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (application_id, account["id"], json.dumps(snapshot), timestamp),
        )
        db.execute(
            """UPDATE registrar_simulations SET student_record_id=?
               WHERE application_id=?""",
            (cursor.lastrowid, application_id),
        )
    return get_student_record(application_id, actor)


def process_acceptance(application_id, actor):
    """SRS 9.5.3/9.5.4: process acceptance and simulate Registrar notification."""
    accounts.require_role(actor, {"administrator"})
    application = _application(application_id)
    if application["status"] != "Accepted":
        raise HTTPException(409, "Only accepted applicants may matriculate")

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _make_tables(db)
        notice = _get_row(db, "official_admission_notices", application_id)
        if notice is None or notice["state"] != "sent" or notice["decision"] != "Accepted":
            raise HTTPException(409, "The official acceptance notice must have been sent")
        intent = _get_row(db, "admission_intents", application_id)
        if intent is None:
            raise HTTPException(409, "No acceptance notification was received from this applicant")
        if intent["processed_at"]:
            raise HTTPException(409, "Enrollment intent has already been processed")

        existing_student = _get_row(db, "admitted_graduate_students", application_id)
        student_id = existing_student["id"] if existing_student else None
        timestamp = _now()
        account = next(
            (u for u in database.users() if u["id"] == application["owner_id"]), None
        )
        registrar_text = (
            "UA-GDAS Registrar Notification (SIMULATION ONLY)\n"
            f"Student record: {student_id if student_id is not None else 'Not yet created'}\n"
            f"Applicant: {application.get('applicant_name', 'Applicant')}\n"
            f"NetID: {(account or {}).get('net_id') or 'Not provided'}\n"
            f"Degree program: {application['degree_program']}\n"
            f"Campus: {application['campus']}\n"
            f"Academic term: {application['term']}\n"
            "Status: Intent to Matriculate\n"
            "No communication with the actual University Registrar was made."
        )
        db.execute(
            """INSERT INTO registrar_simulations
               (application_id, student_record_id, term, notice_text, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (application_id, student_id, application["term"], registrar_text, timestamp),
        )
        db.execute(
            """UPDATE admission_intents SET processed_at=?, processed_by=?
               WHERE application_id=?""",
            (timestamp, actor["id"], application_id),
        )
        application["status"] = "Intent to Matriculate"
        application["last_updated"] = timestamp
        document = dict(application)
        document.pop("id", None)
        db.execute(
            "UPDATE applications SET data=? WHERE id=?",
            (json.dumps(document), application_id),
        )
    return summary(application_id, actor)


def get_student_record(application_id, actor):
    accounts.require_role(actor, {"administrator"})
    _application(application_id)
    with database.connect() as db:
        _make_tables(db)
        result = _get_row(db, "admitted_graduate_students", application_id)
        if not result:
            raise HTTPException(404, "No admitted graduate student record exists")
        record = json.loads(result["record_json"])
        return {"id": result["id"], **record}


def get_registrar_simulation(application_id, actor):
    accounts.require_role(actor, {"administrator"})
    _application(application_id)
    with database.connect() as db:
        _make_tables(db)
        result = _get_row(db, "registrar_simulations", application_id)
        if result is None:
            raise HTTPException(404, "No simulated Registrar notification exists")
        return dict(result)


def get_notice_letter(application_id, actor):
    accounts.require_role(actor, {"administrator"})
    _application(application_id)
    with database.connect() as db:
        _make_tables(db)
        notice = _get_row(db, "official_admission_notices", application_id)
        if notice is None or notice["state"] != "sent":
            raise HTTPException(404, "No delivered official letter is available")
        return dict(notice)


def upload_transcript(application_id, actor, filename, raw, confirmed):
    """Store an explicitly verified PDF outside the public static directory."""
    accounts.require_role(actor, {"administrator"})
    application = _application(application_id)
    if application["status"] not in {"Accepted", "Intent to Matriculate"}:
        raise HTTPException(409, "Official transcript processing requires an accepted applicant")
    with database.connect() as db:
        _make_tables(db)
        if _get_row(db, "admitted_graduate_students", application_id):
            raise HTTPException(
                409, "A student record already exists. Transcript amendments require a separate approved workflow"
            )
    if not confirmed:
        raise HTTPException(422, "Confirm the transcript was received through an approved channel")
    if not raw or len(raw) > MAX_TRANSCRIPT_BYTES:
        raise HTTPException(413, "Official transcript must be a PDF smaller than 10 MB")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(422, "Upload a PDF document")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(422, "Transcript filename must end in .pdf")

    # Generated filename is not derived from user-controlled paths.
    directory = Path(__file__).resolve().parents[1] / "data" / "private_transcripts"
    directory.mkdir(parents=True, exist_ok=True)
    storage_name = f"{application_id}-{secrets.token_hex(16)}.pdf"
    file_path = directory / storage_name
    digest = sha256(raw).hexdigest()
    file_path.write_bytes(raw)
    prior = None
    try:
        with database.connect() as db:
            _make_tables(db)
            prior = _get_row(db, "official_transcripts", application_id)
            db.execute(
                """INSERT INTO official_transcripts
                   (application_id, filename, storage_name, sha256,
                    size_bytes, verified_by, received_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(application_id) DO UPDATE SET
                       filename=excluded.filename,
                       storage_name=excluded.storage_name,
                       sha256=excluded.sha256,
                       size_bytes=excluded.size_bytes,
                       verified_by=excluded.verified_by,
                       received_at=excluded.received_at""",
                (application_id, Path(filename).name, storage_name,
                 digest, len(raw), actor["id"], _now()),
            )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    if prior and prior["storage_name"] != storage_name:
        (directory / prior["storage_name"]).unlink(missing_ok=True)
    return summary(application_id, actor)


def download_transcript(application_id, actor):
    accounts.require_role(actor, {"administrator"})
    _application(application_id)
    with database.connect() as db:
        _make_tables(db)
        transcript = _get_row(db, "official_transcripts", application_id)
        if not transcript:
            raise HTTPException(404, "No verified transcript on file")
        path = Path(__file__).resolve().parents[1] / "data" / "private_transcripts" / transcript["storage_name"]
        if not path.is_file():
            raise HTTPException(404, "Stored transcript is unavailable")
        return path, transcript["filename"]
