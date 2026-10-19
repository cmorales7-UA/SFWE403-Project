"""Locally create the first administrator without public role selection."""
from getpass import getpass
from backend.clients import database
from backend.models.schemas import Registration
from backend.service.accounts import register


def main():
    if any(u['user_type'] == 'administrator' for u in database.users()):
        raise SystemExit('An administrator exists; use account management instead.')
    account = Registration(
        username=input('Administrator username: '),
        password=getpass('Password (8+ characters): '),
        first_name=input('First name: '), last_name=input('Last name: '),
        email=input('Email: '), phone=input('Phone: '),
        security_question_1=input('Security question 1: '),
        security_answer_1=getpass('Answer 1: '),
        security_question_2=input('Security question 2: '),
        security_answer_2=getpass('Answer 2: '),
    )
    created = register(account)
    user = next(u for u in database.users() if u['id'] == created['id'])
    user_id = user.pop('id')
    user['user_type'] = 'administrator'
    database.save_user(user, user_id)
    print('Administrator created. Sign in with POST /api/login in /docs.')


if __name__ == '__main__':
    main()
