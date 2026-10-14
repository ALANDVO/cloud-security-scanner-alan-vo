from fastapi import APIRouter

from .routes import health, scans, findings, ai

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(scans.router)
api_router.include_router(findings.router)
api_router.include_router(ai.router)