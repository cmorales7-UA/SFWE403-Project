from fastapi import APIRouter

from frontend.routes.home import router as home_router
from frontend.routes.auth import router as auth_router
from frontend.routes.dashboard import router as dashboard_router
from frontend.routes.applicant import router as applicant_router
from frontend.routes.degrees import router as degrees_router
from frontend.routes.settings import router as settings_router
from frontend.routes.administrator import router as administrator_router
from frontend.routes.degree_programs import router as degree_programs_router
from frontend.routes.reviews import router as reviews_router

# This router combines all routes that belong to the Front End subsystem.
router = APIRouter()

router.include_router(home_router)
router.include_router(auth_router)
router.include_router(dashboard_router) 
router.include_router(reviews_router)
router.include_router(applicant_router)
router.include_router(degrees_router)
router.include_router(settings_router)
router.include_router(administrator_router)
router.include_router(degree_programs_router)