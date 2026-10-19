"""Account storage, authentication and role rules (SRS 9.2.1 and 9.2.2)."""
import secrets
import sqlite3
import time

from fastapi import HTTPException
from backend.clients import database
from backend.service.security import hash_secret, public_user, verify_secret


def require_role(user, roles):
    if user['user_type'] not in roles:
        raise HTTPException(403, 'Your user type is not authorized for this operation')
    return user


def register(payload):
    data = payload.model_dump()
    for field in ('password', 'security_answer_1', 'security_answer_2'):
        data[field + '_hash'] = hash_secret(data.pop(field))
    data['user_type'] = 'applicant'
    try:
        user_id = database.save_user(data)
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Username or email already exists')
    return public_user(dict(data, id=user_id))


def authenticate(payload):
    user = next((u for u in database.users() if u['username'].casefold() == payload.username.strip().casefold()), None)
    if not user or not verify_secret(payload.password, user['password_hash']):
        raise HTTPException(401, 'Invalid username or password')
    token = secrets.token_urlsafe(32)
    with database.connect() as db:
        db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        db.execute('INSERT INTO sessions VALUES (?,?,?)', (token, user['id'], time.time() + 28800))
    return public_user(user), token


def session_user(token):
    with database.connect() as db:
        session = db.execute('SELECT user_id FROM sessions WHERE token=? AND expires>?', (token, time.time())).fetchone()
    user = next((u for u in database.users() if session and u['id'] == session['user_id']), None)
    if user is None:
        raise HTTPException(401, 'Please log in')
    return user


def logout(token):
    with database.connect() as db:
        db.execute('DELETE FROM sessions WHERE token=?', (token,))


def list_users(actor):
    require_role(actor, {'administrator', 'it_support'})
    return [public_user(u) for u in database.users()]


def update_user(user_id, payload, actor):
    require_role(actor, {'administrator', 'it_support'})
    user = next((u for u in database.users() if u['id'] == user_id), None)
    if user is None:
        raise HTTPException(404, 'User not found')
    changes = payload.model_dump(exclude_none=True)
    if changes.get('user_type', user['user_type']) != user['user_type']:
        require_role(actor, {'administrator'})
    password = changes.pop('new_password', None)
    if password:
        changes['password_hash'] = hash_secret(password)
    user.update(changes)
    user.pop('id')
    try:
        database.save_user(user, user_id)
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'Username or email already exists')
    if password:
        with database.connect() as db:
            db.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
    return public_user(dict(user, id=user_id))
