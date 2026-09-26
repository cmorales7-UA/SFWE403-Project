from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


@router.get(
    "/",
    response_class=HTMLResponse,
    name="home",
)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
    )