"""
API router aggregator.
Collects all route modules and exposes a single `api_router`.
"""
from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.repositories import router as repositories_router
from app.api.routes.projects import router as projects_router
from app.api.routes.deployment import router as deployment_router
from app.api.routes.validation import router as validation_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.deploy import router as deploy_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(repositories_router)
api_router.include_router(projects_router)
api_router.include_router(deployment_router)
api_router.include_router(validation_router)
api_router.include_router(analysis_router)
api_router.include_router(deploy_router)
