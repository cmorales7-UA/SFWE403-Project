
import json
import os
import sqlite3
from pathlib import Path


def connect():
    path = Path(os.environ.get(
        'GDAS_DB_PATH',
        str(Path(__file__).resolve().parents[1] / 'data/gdas.sqlite3')
    ))

    path.parent.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row

    # Existing tables
    db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, email TEXT NOT NULL UNIQUE COLLATE NOCASE, data TEXT NOT NULL)')

    db.execute('CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL)')

    db.execute('CREATE TABLE IF NOT EXISTS programs (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')

    db.execute('CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, program_id INTEGER NOT NULL, data TEXT NOT NULL)')

    db.execute('CREATE INDEX IF NOT EXISTS applications_owner_idx ON applications(owner_id)')

    db.execute('CREATE INDEX IF NOT EXISTS applications_program_idx ON applications(program_id)')

    db.execute('CREATE TABLE IF NOT EXISTS application_messages (id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, actor_id INTEGER NOT NULL, recipient TEXT NOT NULL, kind TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')

    db.execute('CREATE TABLE IF NOT EXISTS recommendation_requests (id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, actor_id INTEGER NOT NULL, reference_number INTEGER NOT NULL, recipient_name TEXT NOT NULL, recipient_email TEXT NOT NULL, login_name TEXT NOT NULL UNIQUE, authorization_code_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')

    # SRS 9.4.4: Reviewer assignments
    db.execute('''
        CREATE TABLE IF NOT EXISTS review_assignments (
            id INTEGER PRIMARY KEY,
            application_id INTEGER NOT NULL,
            reviewer_id INTEGER NOT NULL,
            assigned_by INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            notified_at TEXT,
            UNIQUE(application_id, reviewer_id)
        )
    ''')

    db.execute('CREATE INDEX IF NOT EXISTS review_assignments_reviewer_idx ON review_assignments(reviewer_id)')

    db.execute('CREATE INDEX IF NOT EXISTS review_assignments_application_idx ON review_assignments(application_id)')

    # SRS 9.4.4: Notification history
    # Also supports reminders under SRS 9.4.6.
    db.execute('''
        CREATE TABLE IF NOT EXISTS review_notifications (
            id INTEGER PRIMARY KEY,
            reviewer_id INTEGER NOT NULL,
            advisor_id INTEGER NOT NULL,
            recipient TEXT NOT NULL,
            assignment_ids TEXT NOT NULL,
            kind TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    db.execute('CREATE INDEX IF NOT EXISTS review_notifications_reviewer_idx ON review_notifications(reviewer_id)')

    return db


# Existing User Functions

def users():
    with connect() as db:
        return [
            dict(json.loads(r['data']), id=r['id'])
            for r in db.execute('SELECT * FROM users ORDER BY id')
        ]


def save_user(data, user_id=None):
    with connect() as db:
        if user_id is None:
            cursor = db.execute(
                'INSERT INTO users(username,email,data) VALUES (?,?,?)',
                (data['username'], data['email'], json.dumps(data))
            )
            return cursor.lastrowid

        db.execute(
            'UPDATE users SET username=?,email=?,data=? WHERE id=?',
            (
                data['username'],
                data['email'],
                json.dumps(data),
                user_id
            )
        )

    return user_id


# Existing Degree Program Functions

def programs():
    with connect() as db:
        return [
            dict(json.loads(r['data']), id=r['id'])
            for r in db.execute('SELECT * FROM programs ORDER BY id')
        ]


def save_program(data, program_id=None):
    with connect() as db:
        if program_id is None:
            return db.execute(
                'INSERT INTO programs(data) VALUES (?)',
                (json.dumps(data),)
            ).lastrowid

        db.execute(
            'UPDATE programs SET data=? WHERE id=?',
            (json.dumps(data), program_id)
        )

        return program_id


# Existing Application Functions

def applications():
    with connect() as db:
        return [
            dict(
                json.loads(r['data']),
                id=r['id'],
                owner_id=r['owner_id'],
                program_id=r['program_id']
            )
            for r in db.execute(
                'SELECT * FROM applications ORDER BY id DESC'
            )
        ]


def get_application(application_id):
    with connect() as db:
        row = db.execute(
            'SELECT * FROM applications WHERE id=?',
            (application_id,)
        ).fetchone()

        if row is None:
            return None

        return dict(
            json.loads(row['data']),
            id=row['id'],
            owner_id=row['owner_id'],
            program_id=row['program_id']
        )


def save_application(data, application_id=None):
    document = dict(data)
    document.pop('id', None)

    payload = json.dumps(document)

    with connect() as db:
        if application_id is None:
            row = db.execute(
                'INSERT INTO applications(owner_id,program_id,data) VALUES (?,?,?)',
                (
                    document['owner_id'],
                    document['program_id'],
                    payload
                )
            )

            return row.lastrowid

        db.execute(
            'UPDATE applications SET data=? WHERE id=?',
            (payload, application_id)
        )

        return application_id


# Existing Application Communication

def save_message(
    application_id,
    actor_id,
    recipient,
    kind,
    subject,
    body
):
    with connect() as db:
        db.execute(
            'INSERT INTO application_messages(application_id, actor_id, recipient, kind, subject, body) VALUES(?,?,?,?,?,?)',
            (
                application_id,
                actor_id,
                recipient,
                kind,
                subject,
                body
            )
        )


def messages(application_id):
    with connect() as db:
        return [
            dict(r)
            for r in db.execute(
                'SELECT * FROM application_messages WHERE application_id=? ORDER BY id',
                (application_id,)
            )
        ]


# Existing Recommendation Requests

def save_recommendation_request(
    application_id,
    actor_id,
    number,
    name,
    recipient,
    login_name,
    code_hash
):
    with connect() as db:
        db.execute(
            'INSERT INTO recommendation_requests(application_id,actor_id,reference_number,recipient_name,recipient_email,login_name,authorization_code_hash) VALUES (?,?,?,?,?,?,?)',
            (
                application_id,
                actor_id,
                number,
                name,
                recipient,
                login_name,
                code_hash
            )
        )


def recommendation_requests(application_id):
    with connect() as db:
        return [
            dict(r)
            for r in db.execute(
                'SELECT * FROM recommendation_requests WHERE application_id=? ORDER BY id',
                (application_id,)
            )
        ]


# SRS 9.4.4 - Reviewer Assignments

def save_review_assignment(
    application_id,
    reviewer_id,
    assigned_by,
    due_date
):
    with connect() as db:
        db.execute('''
            INSERT INTO review_assignments
                (application_id, reviewer_id, assigned_by, due_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(application_id, reviewer_id)
            DO UPDATE SET
                due_date = excluded.due_date,
                notified_at = CASE
                    WHEN review_assignments.due_date <> excluded.due_date
                    THEN NULL
                    ELSE review_assignments.notified_at
                END
        ''', (
            application_id,
            reviewer_id,
            assigned_by,
            due_date
        ))

        row = db.execute('''
            SELECT *
            FROM review_assignments
            WHERE application_id=? AND reviewer_id=?
        ''', (
            application_id,
            reviewer_id
        )).fetchone()

        return dict(row)


def review_assignments(application_id=None, reviewer_id=None):
    query = 'SELECT * FROM review_assignments WHERE 1=1'
    parameters = []

    if application_id is not None:
        query += ' AND application_id=?'
        parameters.append(application_id)

    if reviewer_id is not None:
        query += ' AND reviewer_id=?'
        parameters.append(reviewer_id)

    query += ' ORDER BY due_date, id'

    with connect() as db:
        return [
            dict(row)
            for row in db.execute(query, parameters)
        ]


def get_review_assignment(assignment_id):
    with connect() as db:
        row = db.execute(
            'SELECT * FROM review_assignments WHERE id=?',
            (assignment_id,)
        ).fetchone()

        return dict(row) if row else None


# SRS 9.4.4 - Reviewer Notification History

def save_review_notification(
    reviewer_id,
    advisor_id,
    recipient,
    assignment_ids,
    subject,
    body,
    kind='initial'
):
    # Called after successful SMTP delivery.
    if kind not in {'initial', 'reminder'}:
        raise ValueError('Unsupported notification kind')

    if not assignment_ids or len(assignment_ids) != len(set(assignment_ids)):
        raise ValueError(
            'Provide a nonempty list of distinct assignments'
        )

    with connect() as db:
        placeholders = ','.join('?' for _ in assignment_ids)

        rows = db.execute(
            f'SELECT id FROM review_assignments '
            f'WHERE reviewer_id=? AND id IN ({placeholders})',
            [reviewer_id, *assignment_ids]
        ).fetchall()

        if len(rows) != len(assignment_ids):
            raise ValueError(
                'All notification assignments must belong to the reviewer'
            )

        cursor = db.execute('''
            INSERT INTO review_notifications
                (
                    reviewer_id,
                    advisor_id,
                    recipient,
                    assignment_ids,
                    kind,
                    subject,
                    body
                )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            reviewer_id,
            advisor_id,
            recipient,
            json.dumps(assignment_ids),
            kind,
            subject,
            body
        ))

        if kind == 'initial':
            db.executemany('''
                UPDATE review_assignments
                SET notified_at=CURRENT_TIMESTAMP
                WHERE id=? AND reviewer_id=?
            ''', [
                (assignment_id, reviewer_id)
                for assignment_id in assignment_ids
            ])

        return cursor.lastrowid


def review_notifications(reviewer_id=None):
    query = 'SELECT * FROM review_notifications'
    parameters = []

    if reviewer_id is not None:
        query += ' WHERE reviewer_id=?'
        parameters.append(reviewer_id)

    query += ' ORDER BY id DESC'

    with connect() as db:
        records = [
            dict(row)
            for row in db.execute(query, parameters)
        ]

    for record in records:
        record['assignment_ids'] = json.loads(
            record['assignment_ids']
        )

    return records
