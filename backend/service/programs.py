"""Graduate program retrieval and persistence (SRS 9.2.4 and 9.2.5)."""
from fastapi import HTTPException
from backend.clients import database
from backend.service.accounts import require_role


def list_programs(actor):
    require_role(actor, {'administrator', 'advisor'})
    return database.programs()


def get_program(program_id, actor):
    programs = list_programs(actor)
    program = next((p for p in programs if p['id'] == program_id), None)
    if program is None:
        raise HTTPException(404, 'Degree program not found')
    return program


def create_program(payload, actor):
    require_role(actor, {'administrator', 'advisor'})
    data = payload.model_dump(mode='json')
    return dict(data, id=database.save_program(data))


def update_program(program_id, payload, actor):
    get_program(program_id, actor)
    data = payload.model_dump(mode='json')
    database.save_program(data, program_id)
    return dict(data, id=program_id)
