"""Liveness and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import Container, get_container
from app.api.schemas.common import HealthStatus
from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus, summary="Liveness probe")
async def health(settings: Settings = Depends(get_settings)) -> HealthStatus:
    """Cheap check: the process is up. Never touches downstream services."""
    return HealthStatus(
        status="ok",
        service=settings.app_name,
        version="1.0.0",
        environment=settings.environment,
    )


@router.get("/ready", response_model=HealthStatus, summary="Readiness probe")
async def ready(
    response: Response,
    settings: Settings = Depends(get_settings),
    container: Container = Depends(get_container),
) -> HealthStatus:
    """Verifies the dependencies a request actually needs before serving traffic."""
    store_ok = await container.store.health()
    llm_ok = await container.llm.health()

    dependencies = {
        "vector_store": "ok" if store_ok else "unavailable",
        "llm": "ok" if llm_ok else "degraded",
        "embeddings": container.embeddings.model_name,
    }

    if not store_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthStatus(
        status="ok" if store_ok and llm_ok else "degraded",
        service=settings.app_name,
        version="1.0.0",
        environment=settings.environment,
        dependencies=dependencies,
    )
