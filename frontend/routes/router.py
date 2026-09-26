from fastapi import APIRouter

from frontend.routes.home import router as home_router
from frontend.routes.auth import router as auth_router
from frontend.routes.dashboard import router as dashboard_router


# This router combines all routes that belong to the Front End subsystem.
router = APIRouter()

router.include_router(home_router)
router.include_router(auth_router)
router.include_router(dashboard_router)