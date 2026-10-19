"""Independent backend launcher; leaves the existing main.py untouched."""
from fastapi import FastAPI
from backend.routes.api import router

app = FastAPI(title='UA-GDAS Backend', version='1.0.0')
app.include_router(router)
