import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.clients import database as storage
from backend.service.security import verify_secret


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('GDAS_DB_PATH', str(tmp_path / 'test.sqlite3'))
    with TestClient(app) as client:
        yield client


def account(username='elend'):
    return dict(username=username, password='Testing123!', first_name='Elend',
                last_name='Hudson', email=f'{username}@example.com', phone='5551234567',
                net_id='', security_question_1='First pet?', security_answer_1='cat',
                security_question_2='First school?', security_answer_2='school')


def sign_in(client, role='applicant', username='elend'):
    response = client.post('/api/users', json=account(username))
    assert response.status_code == 201
    user = storage.users()[-1]
    user['user_type'] = role
    user_id = user.pop('id')
    storage.save_user(user, user_id)
    assert client.post('/api/login', json={'username': username, 'password': 'Testing123!'}).status_code == 200
    return user_id


def program():
    return dict(degree_name='Software Engineering', degree_level='masters',
                degree_college='Engineering', degree_description='A graduate program',
                campus_offered=['main', 'online'], terms_offered=['Fall 2027'],
                degree_requirements='Bachelor degree', application_deadline='2027-01-15',
                application_fee='90.00', sponsor_question='Sponsor?',
                ta_ra_question='Assistantship?', funding_question='Funding?',
                english_test_question='Test?', english_score_question='Score?',
                other_requirements='Resume', program_contact='grad@example.com')


def test_account_persistence_and_secret_hashes(client):
    response = client.post('/api/users', json=account())
    assert response.status_code == 201
    assert response.json()['user_type'] == 'applicant'
    assert not any('hash' in key or 'password' in key for key in response.json())
    saved = storage.users()[0]
    for key, value in account().items():
        if key in {'password', 'security_answer_1', 'security_answer_2'}:
            assert key not in saved
            assert verify_secret(value, saved[key + '_hash'])
        else:
            assert saved[key] == value
    # A separate connection/client sees the same persisted record.
    with TestClient(app) as other:
        assert other.post('/api/login', json={'username': 'elend', 'password': 'Testing123!'}).status_code == 200


def test_duplicate_and_invalid_registration(client):
    assert client.post('/api/users', json=account()).status_code == 201
    assert client.post('/api/users', json=account('ELEND')).status_code == 409
    data = account('other'); data['user_type'] = 'administrator'
    assert client.post('/api/users', json=data).status_code == 422
    data = account('other'); data['password'] = 'short'
    assert client.post('/api/users', json=data).status_code == 422


def test_authorization_and_login(client):
    assert client.get('/api/users').status_code == 401
    assert client.post('/api/login', json={'username': 'no', 'password': 'no'}).status_code == 401
    sign_in(client)
    assert client.get('/api/users').status_code == 403
    assert client.post('/api/programs', json=program()).status_code == 403


def test_admin_manage_accounts(client):
    sign_in(client, 'administrator', 'admin')
    created = client.post('/api/users', json=account()).json()
    response = client.patch(f"/api/users/{created['id']}", json={'first_name': 'Updated', 'user_type': 'reviewer'})
    assert response.status_code == 200
    assert response.json()['first_name'] == 'Updated'
    assert storage.users()[-1]['user_type'] == 'reviewer'
    assert len(client.get('/api/users').json()) == 2
    assert client.patch('/api/users/9999', json={'first_name': 'X'}).status_code == 404
    assert client.patch(f"/api/users/{created['id']}", json={'email': 'bad'}).status_code == 422


def test_it_can_edit_but_cannot_assign_roles(client):
    sign_in(client, 'it_support', 'support')
    created = client.post('/api/users', json=account()).json()
    path = f"/api/users/{created['id']}"
    assert client.patch(path, json={'phone': '5559999999'}).status_code == 200
    assert client.patch(path, json={'user_type': 'administrator'}).status_code == 403


def test_program_fields_and_browser_integration(client):
    sign_in(client, 'administrator')
    response = client.post('/api/programs', json=program())
    assert response.status_code == 201
    saved = storage.programs()[0]
    assert all(saved[key] == value for key, value in program().items())
    assert client.post('/api/programs', json=dict(program(), application_fee='-1')).status_code == 422
    assert client.post('/api/programs', json=dict(program(), campus_offered=[])).status_code == 422


def test_logout_invalidates_session(client):
    sign_in(client, 'administrator')
    token = client.cookies.get('gdas_session')
    assert client.post('/api/logout').status_code == 204
    client.cookies.set('gdas_session', token)
    assert client.get('/api/users').status_code == 401


def test_password_reset_invalidates_previous_session(client):
    user_id = sign_in(client, 'administrator')
    assert client.patch(f'/api/users/{user_id}', json={'new_password': 'Changed123!'}).status_code == 200
    assert client.get('/api/users').status_code == 401
    assert client.post('/api/login', json={'username': 'elend', 'password': 'Testing123!'}).status_code == 401
    assert client.post('/api/login', json={'username': 'elend', 'password': 'Changed123!'}).status_code == 200


@pytest.mark.parametrize('role,path', [('administrator', '/administrator'), ('advisor', '/advisor')])
def test_program_retrieval_and_update(client, role, path):
    sign_in(client, role)
    created = client.post('/api/programs', json=program()).json()
    program_id = created['id']
    assert client.get('/api/programs').json() == [created]
    assert client.get(f'/api/programs/{program_id}').json() == created
    changes = dict(program(), degree_requirements='Updated requirements', application_fee='105.50',
                   english_score_question='Minimum TOEFL 90', application_deadline='2027-02-01')
    assert client.put(f'/api/programs/{program_id}', json=changes).status_code == 200
    assert storage.programs()[0]['degree_requirements'] == 'Updated requirements'
    with TestClient(app) as other:
        other.cookies.update(client.cookies)
        saved = other.get(f'/api/programs/{program_id}').json()
        assert all(saved[k] == v for k, v in changes.items())
    assert client.put(f'/api/programs/{program_id}', json=dict(changes, application_fee='-1')).status_code == 422
    assert storage.programs()[0]['application_fee'] == '105.50'
    assert client.get('/api/programs/9999').status_code == 404
    assert client.put('/api/programs/9999', json=changes).status_code == 404


@pytest.mark.parametrize('role', ['applicant', 'reviewer', 'reference', 'it_support'])
def test_program_management_forbidden_for_other_roles(client, role):
    sign_in(client, role)
    assert client.get('/api/programs').status_code == 403
    assert client.get('/api/programs/1').status_code == 403
    assert client.put('/api/programs/1', json=program()).status_code == 403


def test_program_management_requires_login(client):
    assert client.get('/api/programs').status_code == 401
    assert client.get('/api/programs/1').status_code == 401
    assert client.put('/api/programs/1', json=program()).status_code == 401
