from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# This router handles Graduate Degree pages.
router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# This route displays the available Graduate Degree programs.
@router.get(
    "/applicant/graduate-degrees",
    response_class=HTMLResponse,
    name="applicant_graduate_degrees",
)
async def applicant_graduate_degrees(request: Request):

    search_query = request.query_params.get("q", "")
    selected_level = request.query_params.get("level", "")
    selected_campus = request.query_params.get("campus", "")

    return templates.TemplateResponse(
        request=request,
        name="applicant/graduate_degrees.html",
        context={
            "degrees": [],
            "selected_degree": None,
            "search_query": search_query,
            "selected_level": selected_level,
            "selected_campus": selected_campus,
        },
    )