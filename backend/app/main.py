"""Application FastAPI — Coach IA GTB.

Point d'entrée principal du backend. Configure :
  - CORS
  - Middlewares (logging, métriques)
  - Routers API V1
  - Hooks de cycle de vie (lifespan)
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import agent, alarms, energy, health, points, sites
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Hooks startup/shutdown."""
    logger.info("app.startup", env=settings.app_env, version="0.1.0")
    # TODO: démarrer le NiagaraPoller en tâche de fond ici si configuré
    yield
    logger.info("app.shutdown")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend du Coach IA GTB — PFEE EPITA × AER",
    lifespan=lifespan,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["health"])
app.include_router(sites.router, prefix=settings.api_v1_prefix, tags=["sites"])
app.include_router(points.router, prefix=settings.api_v1_prefix, tags=["points"])
app.include_router(alarms.router, prefix=settings.api_v1_prefix, tags=["alarms"])
app.include_router(agent.router, prefix=settings.api_v1_prefix, tags=["agent"])
app.include_router(energy.router, prefix=settings.api_v1_prefix, tags=["energy"])


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "env": settings.app_env,
        "docs": "/docs",
    }
