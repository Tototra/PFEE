"""Endpoints de healthcheck."""

from datetime import datetime

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Healthcheck simple — utilisé par Docker / load balancer."""
    return {
        "status": "ok",
        "env": settings.app_env,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready")
async def ready() -> dict:
    """Readiness check — vérifie que toutes les dépendances sont opérationnelles.

    TODO: tester DB, Redis, ChromaDB, Mistral API.
    """
    return {"status": "ready"}
