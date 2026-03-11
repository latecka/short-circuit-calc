# Short-Circuit Calculator - REST API (V1b)

from fastapi import APIRouter

from .auth import router as auth_router
from .projects import router as projects_router
from .calculations import router as calculations_router
from .scenarios import router as scenarios_router
from .audit import router as audit_router
from .export import router as export_router
from .import_ import router as import_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(calculations_router)
api_router.include_router(scenarios_router)
api_router.include_router(audit_router)
api_router.include_router(export_router)
api_router.include_router(import_router)
