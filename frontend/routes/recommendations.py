from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


def get_recommendation_request(request: Request):
    """
    Backend integration point.

    The backend should return the recommendation request
    associated with the currently authenticated reference.
    """

    return None


@router.get(
    "/reference/recommendation",
    response_class=HTMLResponse,
    name="reference_recommendation",
)
async def reference_recommendation(request: Request):

    recommendation_request = get_recommendation_request(
        request
    )

    return templates.TemplateResponse(
        request=request,
        name="reference/recommendation.html",
        context={
            "recommendation_request":
                recommendation_request,

            # Enable after backend authorization and
            # persistent submission are implemented.
            "submission_enabled": False,
        },
    )