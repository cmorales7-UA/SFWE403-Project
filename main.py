from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from frontend.routes.router import router as frontend_router
from backend.routes.api import router as api_router


app = FastAPI(title="UA-GDAS")


app.mount(
    "/static",
    StaticFiles(directory="frontend/static"),
    name="static",
)


app.include_router(frontend_router)
app.include_router(api_router)