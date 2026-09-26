from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# This router handles account and authentication pages.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# This route displays the Create Account page.
@router.get(
    "/create-account",
    response_class=HTMLResponse,
    name="create_account",
)
async def create_account(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/create_account.html",
    )

# This route displays the Login page.
@router.get(
    "/login",
    response_class=HTMLResponse,
    name="login",
)
async def login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
    )