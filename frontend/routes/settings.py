from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


def get_return_to(request: Request):
    return_to = request.query_params.get(
        "return_to",
        "/",
    )

    if (
        not return_to.startswith("/")
        or return_to.startswith("//")
    ):
        return "/"

    return return_to


def get_security_questions(request: Request):
    """
    Backend integration point.

    The backend should return the two security questions
    associated with the authenticated user's account.
    """

    return {
        "security_question_1": None,
        "security_question_2": None,
    }


@router.get(
    "/settings",
    response_class=HTMLResponse,
    name="settings",
)
async def settings(request: Request):

    return_to = get_return_to(request)

    encoded_return_to = quote(
        return_to,
        safe="/",
    )

    return templates.TemplateResponse(
        request=request,
        name="settings/index.html",
        context={
            "return_to": return_to,
            "change_password_url": (
                "/settings/change-password"
                f"?return_to={encoded_return_to}"
            ),
        },
    )


@router.get(
    "/settings/change-password",
    response_class=HTMLResponse,
    name="change_password",
)
async def change_password(request: Request):

    return_to = get_return_to(request)

    encoded_return_to = quote(
        return_to,
        safe="/",
    )

    questions = get_security_questions(request)

    return templates.TemplateResponse(
        request=request,
        name="settings/change_password.html",
        context={
            "return_to": return_to,
            "settings_url": (
                f"/settings?return_to={encoded_return_to}"
            ),
            "security_question_1": questions[
                "security_question_1"
            ],
            "security_question_2": questions[
                "security_question_2"
            ],

            # Set to True after the backend POST
            # password-change flow is connected.
            "password_change_enabled": False,
        },
    )