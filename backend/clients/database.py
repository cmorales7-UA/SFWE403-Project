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
