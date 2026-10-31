
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.service import accounts


# Account and authentication pages.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# Create Account
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


# Login
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


# Sign Out
@router.post(
    "/logout",
    name="sign_out",
)
async def sign_out(request: Request):

    token = request.cookies.get("gdas_session", "")

    if token:
        accounts.logout(token)

    response = RedirectResponse(
        url="/login",
        status_code=303
    )

    # Remove the authentication cookie.
    response.delete_cookie(
        key="gdas_session",
        path="/"
    )

    return response
