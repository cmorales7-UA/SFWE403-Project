from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from frontend.routes.router import router as frontend_router


app = FastAPI(title="UA-GDAS")


app.mount(
    "/static",
    StaticFiles(directory="frontend/static"),
    name="static",
)


app.include_router(frontend_router)