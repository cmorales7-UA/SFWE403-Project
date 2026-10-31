
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.service import accounts
from frontend.routes.router import router as frontend_router
from backend.routes.api import router as api_router


app = FastAPI(title="UA-GDAS")


# URL prefixes and their authorized roles.
ROLE_PATHS = {
    "applicant": "applicant",
    "administrator": "administrator",
    "advisor": "advisor",
    "reviewer": "reviewer",
    "reference": "reference",
    "it-support": "it_support",
}


# Pages that do not require authentication.
PUBLIC_PAGES = {
    "/",
    "/login",
    "/create-account",
    "/graduate-degrees",
}


@app.middleware("http")
async def protect_private_routes(request: Request, call_next):

    path = request.url.path.rstrip("/") or "/"
    method = request.method

    # Public pages and static assets.
    if path in PUBLIC_PAGES or path.startswith("/static/"):
        return await call_next(request)

    # Public account registration and login.
    if method == "POST" and path in {
        "/api/login",
        "/api/users",
    }:
        return await call_next(request)

    # The logout endpoint handles clearing the session.
    if method == "POST" and path == "/logout":
        return await call_next(request)

    # Browser favicon requests do not need authentication.
    if path == "/favicon.ico":
        return await call_next(request)

    # Verify the stored login session.
    try:
        user = accounts.session_user(
            request.cookies.get("gdas_session", "")
        )
    except HTTPException as error:
        if error.status_code != 401:
            raise

        # API requests receive an authentication error.
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"}
            )

        # Unauthenticated visitors are sent to login.
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # Save the authenticated user for this request.
    request.state.user = user

    # Determine which role owns the requested page.
    path_role = path.strip("/").split("/")[0]
    required_role = ROLE_PATHS.get(path_role)

    # Prevent users from opening another role's pages.
    if required_role and user["user_type"] != required_role:
        return PlainTextResponse(
            "403 Forbidden",
            status_code=403
        )

    return await call_next(request)


app.mount(
    "/static",
    StaticFiles(directory="frontend/static"),
    name="static",
)

app.include_router(frontend_router)
app.include_router(api_router)
