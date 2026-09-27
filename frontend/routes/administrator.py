from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# This router handles Graduate College Administrator pages.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")

# This route displays the Manage Users GUI.
@router.get(
    "/administrator/manage-users",
    response_class=HTMLResponse,
    name="manage_users",
)
async def manage_users(request: Request):

    search_query = request.query_params.get("q", "")
    selected_user_type = request.query_params.get("user_type", "")

    return templates.TemplateResponse(
        request=request,
        name="administrator/manage_users.html",
        context={
            "users": [],
            "selected_user": None,
            "search_query": search_query,
            "selected_user_type": selected_user_type,
        },
    )