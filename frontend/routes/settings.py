from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# This router handles account settings pages.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# This route displays the Change Password GUI.
@router.get(
    "/settings/change-password",
    response_class=HTMLResponse,
    name="change_password",
)
async def change_password(request: Request):

    return_to = request.query_params.get("return_to", "/")

    # This keeps the return destination inside the application.
    if not return_to.startswith("/") or return_to.startswith("//"):
        return_to = "/"

    return templates.TemplateResponse(
        request=request,
        name="settings/change_password.html",
        context={
            "return_to": return_to,
        },
    )