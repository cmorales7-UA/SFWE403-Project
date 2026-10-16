"""HTTP endpoints; business rules live in service, database access in clients."""
from fastapi import APIRouter, Depends, Request, Response
from backend.models.schemas import Login, ProgramCreate, Registration, UserUpdate
from backend.service import accounts, programs

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
