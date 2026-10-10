from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="frontend/templates")


# Temporary frontend data.
# Replace this list with backend degree-program data later.
MOCK_DEGREES = [
    {
        "id": 1,
        "name": "Computer Science",
        "level": "Masters",
        "level_value": "masters",
        "college": "College of Science",
        "campus": "Main, Online",
        "campus_values": ["main", "online"],
        "term": "Fall 2027",
        "application_deadline": "January 15, 2027",
        "application_fee": "$90",
        "description": (
            "Graduate study focused on advanced computing topics, "
            "software systems, and computer science research."
        ),
        "requirements": (
            "Applicants must provide required academic history, "
            "transcripts, application materials, and program-specific "
            "information."
        ),
        "other_requirements": (
            "Additional requirements may be specified by the degree program."
        ),
        "contact_information": (
            "Graduate Program Office"
        ),
    },
    {
        "id": 2,
        "name": "Software Engineering",
        "level": "Masters",
        "level_value": "masters",
        "college": "College of Engineering",
        "campus": "Main, Online",
        "campus_values": ["main", "online"],
        "term": "Spring 2028",
        "application_deadline": "October 15, 2027",
        "application_fee": "$90",
        "description": (
            "Graduate study focused on software design, development, "
            "architecture, testing, and engineering practices."
        ),
        "requirements": (
            "Applicants must provide academic history, transcripts, "
            "application materials, and all required supplemental information."
        ),
        "other_requirements": (
            "Program-specific supplemental questions may apply."
        ),
        "contact_information": (
            "Graduate Program Office"
        ),
    },
    {
        "id": 3,
        "name": "Data Science",
        "level": "Doctorate",
        "level_value": "doctorate",
        "college": "Graduate College",
        "campus": "Main",
        "campus_values": ["main"],
        "term": "Fall 2028",
        "application_deadline": "December 1, 2027",
        "application_fee": "$90",
        "description": (
            "Doctoral study involving advanced data analysis, "
            "computational methods, and research."
        ),
        "requirements": (
            "Applicants must provide the required academic background, "
            "supporting documents, and program-specific application materials."
        ),
        "other_requirements": (
            "Additional research or academic information may be requested."
        ),
        "contact_information": (
            "Graduate Program Office"
        ),
    },
]


def degree_browser_context(
    q: str,
    level: str,
    campus: str,
    degree: int | None,
):
    # Start with all available degree programs.
    filtered_degrees = MOCK_DEGREES.copy()

    search_query = q.strip().lower()

    # Filter by degree name or college.
    if search_query:
        filtered_degrees = [
            item
            for item in filtered_degrees
            if search_query in item["name"].lower()
            or search_query in item["college"].lower()
        ]

    # Filter by degree level.
    if level:
        filtered_degrees = [
            item
            for item in filtered_degrees
            if item["level_value"] == level
        ]

    # Filter by campus.
    if campus:
        filtered_degrees = [
            item
            for item in filtered_degrees
            if campus in item["campus_values"]
        ]

    # Retrieve the selected degree.
    selected_degree = None

    if degree is not None:
        selected_degree = next(
            (
                item
                for item in MOCK_DEGREES
                if item["id"] == degree
            ),
            None,
        )

    return {
        "degrees": filtered_degrees,
        "selected_degree": selected_degree,
        "search_query": q,
        "selected_level": level,
        "selected_campus": campus,
    }


@router.get(
    "/applicant/graduate-degrees",
    response_class=HTMLResponse,
    name="applicant_graduate_degrees",
)
async def applicant_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/applicant/graduate-degrees"
    )

    context["degree_apply_action"] = (
        "/applicant/application"
    )

    return templates.TemplateResponse(
        request=request,
        name="applicant/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/administrator/graduate-degrees",
    response_class=HTMLResponse,
    name="administrator_graduate_degrees",
)
async def administrator_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/administrator/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="administrator/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/advisor/graduate-degrees",
    response_class=HTMLResponse,
    name="advisor_graduate_degrees",
)
async def advisor_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/advisor/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="advisor/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/reviewer/graduate-degrees",
    response_class=HTMLResponse,
    name="reviewer_graduate_degrees",
)
async def reviewer_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/reviewer/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="reviewer/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/it-support/graduate-degrees",
    response_class=HTMLResponse,
    name="it_support_graduate_degrees",
)
async def it_support_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/it-support/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="it_support/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/reference/graduate-degrees",
    response_class=HTMLResponse,
    name="reference_graduate_degrees",
)
async def reference_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/reference/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="reference/graduate_degrees.html",
        context=context,
    )


@router.get(
    "/graduate-degrees",
    response_class=HTMLResponse,
    name="public_graduate_degrees",
)
async def public_graduate_degrees(
    request: Request,
    q: str = "",
    level: str = "",
    campus: str = "",
    degree: int | None = None,
):
    context = degree_browser_context(
        q,
        level,
        campus,
        degree,
    )

    context["degree_browser_action"] = (
        "/graduate-degrees"
    )

    return templates.TemplateResponse(
        request=request,
        name="degrees/public_degree_browser.html",
        context=context,
    )