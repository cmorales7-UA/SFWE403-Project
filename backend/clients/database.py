import json
import os
import sqlite3
from pathlib import Path


def connect():
    path = Path(os.environ.get('GDAS_DB_PATH', str(Path(__file__).resolve().parents[1] / 'data/gdas.sqlite3')))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, email TEXT NOT NULL UNIQUE COLLATE NOCASE, data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS programs (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, program_id INTEGER NOT NULL, data TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS applications_owner_idx ON applications(owner_id)')
    db.execute('CREATE INDEX IF NOT EXISTS applications_program_idx ON applications(program_id)')
    db.execute('CREATE TABLE IF NOT EXISTS application_messages (id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, actor_id INTEGER NOT NULL, recipient TEXT NOT NULL, kind TEXT NOT NULL, subject TEXT NOT NULL, body TEXT NOT NULL, sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE IF NOT EXISTS recommendation_requests (id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, actor_id INTEGER NOT NULL, reference_number INTEGER NOT NULL, recipient_name TEXT NOT NULL, recipient_email TEXT NOT NULL, login_name TEXT NOT NULL UNIQUE, authorization_code_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    return db


def users():
    with connect() as db:
        return [dict(json.loads(r['data']), id=r['id']) for r in db.execute('SELECT * FROM users ORDER BY id')]


def save_user(data, user_id=None):
    with connect() as db:
        if user_id is None:
            cursor = db.execute('INSERT INTO users(username,email,data) VALUES (?,?,?)', (data['username'], data['email'], json.dumps(data)))
            return cursor.lastrowid
        db.execute('UPDATE users SET username=?,email=?,data=? WHERE id=?', (data['username'], data['email'], json.dumps(data), user_id))
    return user_id


def programs():
    with connect() as db:
        return [dict(json.loads(r['data']), id=r['id']) for r in db.execute('SELECT * FROM programs ORDER BY id')]


def save_program(data, program_id=None):
    with connect() as db:
        if program_id is None:
            return db.execute('INSERT INTO programs(data) VALUES (?)', (json.dumps(data),)).lastrowid
        db.execute('UPDATE programs SET data=? WHERE id=?', (json.dumps(data), program_id))
        return program_id


def applications():
    with connect() as db:
        return [dict(json.loads(r['data']), id=r['id'], owner_id=r['owner_id'], program_id=r['program_id'])
                for r in db.execute('SELECT * FROM applications ORDER BY id DESC')]


def get_application(application_id):
    with connect() as db:
        row = db.execute('SELECT * FROM applications WHERE id=?', (application_id,)).fetchone()
        if row is None:
            return None
        return dict(json.loads(row['data']), id=row['id'], owner_id=row['owner_id'], program_id=row['program_id'])


def save_application(data, application_id=None):
    document = dict(data)
    document.pop('id', None)
    payload = json.dumps(document)
    with connect() as db:
        if application_id is None:
            row = db.execute('INSERT INTO applications(owner_id,program_id,data) VALUES (?,?,?)',
                             (document['owner_id'], document['program_id'], payload))
            return row.lastrowid
        db.execute('UPDATE applications SET data=? WHERE id=?', (payload, application_id))
        return application_id


def save_message(application_id, actor_id, recipient, kind, subject, body):
    with connect() as db:
        db.execute('INSERT INTO application_messages(application_id, actor_id, recipient, kind, subject, body) VALUES(?,?,?,?,?,?)',
                   (application_id, actor_id, recipient, kind, subject, body))


def messages(application_id):
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT * FROM application_messages WHERE application_id=? ORDER BY id', (application_id,))]


def save_recommendation_request(application_id, actor_id, number, name, recipient, login_name, code_hash):
    with connect() as db:
        db.execute('INSERT INTO recommendation_requests(application_id,actor_id,reference_number,recipient_name,recipient_email,login_name,authorization_code_hash) VALUES (?,?,?,?,?,?,?)',
                   (application_id, actor_id, number, name, recipient, login_name, code_hash))


def recommendation_requests(application_id):
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT * FROM recommendation_requests WHERE application_id=? ORDER BY id', (application_id,))]
