"""
Punto di ingresso dell'aplicazione FastAPI.

Questo e il modulo principale che:
- Configura l]applicazione FastAPI
- Stabilisce le rotte
- Gestisce il ciclo di vita dell'applicazione(avvio/arresto)

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

from collections.abc import AsyncIterable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.slack_webhook import router as slack_router
from app.config.settings import settings
from app.repositories.redis_client import close_redis, init_redis


@asynccontextmanager
async def lifespan(app:FastAPI) ->AsyncIterable[None]:
    """
    Application lifecycle manager.

    Startup: initialize external connections (Redis, future: DB, Langfuse).
    Shutdown: cleanup connections gracefully.

    """
    #Startup
    print(f"[startup]Application starting in {settings.app_env} mode")
    print(f"[startup] Log level: {settings.log_level}")
    print(f"[startup] OpenAi default model: {settings.openai_model_default}")
    # Initialize Redis (fail fast if unreachable)
    print("[startup] Initializing Redis connection...")
    await init_redis()
    print("[startup] Redis connected")
    yield
    #Shutdown
    print("[shutdown] Closing Redis connection...")
    await close_redis()
    print("[shutdown] Application shutdown complete")
# ============================================================
# FastAPI application instance
# ============================================================
app = FastAPI(
    title="It Heldesk Slack Assistant",

    description=(
        "Ai powered Slakc assistant for internal IT support requests"
        "Multi-agent system with hitl escalation"),
        version="0.1.0",
        lifespan = lifespan,
        # Disable docs in production for security
        docs_url="/docs" if not settings.is_production else None,
    )
# ============================================================
# Health endpoint
# ============================================================
@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """
    Liveness probe endpoint.

    Returns 200 OK if the application process is running.
    Does NOT check dependencies (DB, Redis, etc.) — that's the readiness probe.

    Used by:
    - Docker Compose healthcheck
    - Azure Container Apps health probes
    - Manual debugging
    """
    return {
        "status": "ok",
        "service": "helpdesk-slack-assistant",
        "version": "0.1.0",
        "environment": settings.app_env,
    }

@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    """
    Root endpoint — minimal info, redirects to docs.
    """
    return {
        "service": "IT Helpdesk Slack Assistant",
        "docs": "/docs",
        "health": "/health",
    }
# ============================================================
# Slack routes
# ============================================================
app.include_router(slack_router)
