"""HTTP endpoints; business rules live in service, database access in clients."""
from fastapi import APIRouter, Depends, Request, Response
from backend.models.schemas import Login, ProgramCreate, Registration, UserUpdate
from backend.service import accounts, programs, applications
from backend.models.application_schemas import (
    ApplicationCreate, ApplicationUpdate, PreliminaryReview,
    ApplicantMessage, ReferenceRequest,
)

router = APIRouter(prefix='/api')


def current_user(request: Request):
    return accounts.session_user(request.cookies.get('gdas_session', ''))


@router.post('/users', status_code=201)
def register(payload: Registration):
    return accounts.register(payload)


@router.post('/login')
def login(payload: Login, request: Request, response: Response):
    user, token = accounts.authenticate(payload)
    response.set_cookie('gdas_session', token, httponly=True, samesite='strict',
                        secure=request.url.scheme == 'https', max_age=28800)
    return user


@router.post('/logout', status_code=204)
def logout(request: Request, response: Response):
    accounts.logout(request.cookies.get('gdas_session', ''))
    response.delete_cookie('gdas_session')


@router.get('/users')
def list_users(actor=Depends(current_user)):
    return accounts.list_users(actor)


@router.patch('/users/{user_id}')
def update_user(user_id: int, payload: UserUpdate, actor=Depends(current_user)):
    return accounts.update_user(user_id, payload, actor)


@router.post('/programs', status_code=201)
def create_program(payload: ProgramCreate, actor=Depends(current_user)):
    return programs.create_program(payload, actor)


@router.get('/programs')
def list_programs(actor=Depends(current_user)):
    return programs.list_programs(actor)


@router.get('/programs/{program_id}')
def get_program(program_id: int, actor=Depends(current_user)):
    return programs.get_program(program_id, actor)


@router.put('/programs/{program_id}')
def update_program(program_id: int, payload: ProgramCreate, actor=Depends(current_user)):
    return programs.update_program(program_id, payload, actor)


# SRS 9.4.1: retrieve and update only authorized applications.
@router.post('/applications', status_code=201)
def create_application(payload: ApplicationCreate, actor=Depends(current_user)):
    return applications.create_application(payload, actor)


@router.get('/applications')
def list_applications(actor=Depends(current_user)):
    return applications.list_applications(actor)


@router.get('/applications/{application_id}')
def get_application(application_id: int, actor=Depends(current_user)):
    return applications.get_application(application_id, actor)


@router.patch('/applications/{application_id}')
def update_application(application_id: int, payload: ApplicationUpdate, actor=Depends(current_user)):
    return applications.update_application(application_id, payload, actor)


# SRS 9.4.2: advisor preliminary review, missing information, and references.
@router.post('/applications/{application_id}/preliminary-review')
def preliminary_review(application_id: int, payload: PreliminaryReview, actor=Depends(current_user)):
    return applications.preliminary_review(application_id, payload, actor)


@router.post('/applications/{application_id}/request-information')
def request_information(application_id: int, actor=Depends(current_user)):
    return applications.request_information(application_id, actor)


@router.post('/applications/{application_id}/recommendation-requests')
def request_recommendation(application_id: int, payload: ReferenceRequest, actor=Depends(current_user)):
    return applications.request_recommendation(application_id, payload, actor)


# SRS 9.4.3: send email to applicant before a final decision.
@router.post('/applications/{application_id}/messages')
def send_application_message(application_id: int, payload: ApplicantMessage, actor=Depends(current_user)):
    return applications.message_applicant(application_id, payload, actor)
