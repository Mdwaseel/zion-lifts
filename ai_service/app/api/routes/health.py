"""Liveness and readiness endpoints.

Three, not two, because there are three different questions. `/health` asks
whether the process is up. `/ready` asks whether it can answer a question.
`/ready/worker` asks whether a document can be ingested — a different set of
dependencies that fails independently of the other two.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import Container, get_container
from app.api.schemas.common import HealthStatus
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.security import require_internal_token

logger = get_logger(__name__)

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
    """Verifies the dependencies a *request* needs before serving traffic.

    Deliberately says nothing about the ingestion worker. Readiness answers one
    question — should this instance receive traffic — and an API that can answer
    questions perfectly well should not be pulled out of the load balancer
    because a worker somewhere is down. Ingestion health is `/ready/worker`.
    """
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


@router.get(
    "/ready/worker",
    response_model=HealthStatus,
    summary="Ingestion readiness",
    dependencies=[Depends(require_internal_token)],
)
async def worker_ready(
    response: Response,
    settings: Settings = Depends(get_settings),
    container: Container = Depends(get_container),
) -> HealthStatus:
    """Can a document be ingested right now?

    A different set of dependencies from the one above, and separate because
    they fail independently: ingestion needs a broker and a worker consuming
    from it, neither of which a chat request touches.

    Guarded by the internal token — the reply names the broker and enumerates
    live workers, which is operational detail rather than public health.
    """
    store_ok = await container.store.health()
    broker_ok, workers = await _broker_health(settings)

    dependencies = {
        "vector_store": "ok" if store_ok else "unavailable",
        "broker": "ok" if broker_ok else "unavailable",
        "queue": settings.celery_task_queue,
        "workers": str(len(workers)),
        "worker_names": ", ".join(sorted(workers)) or "none",
    }

    healthy = store_ok and broker_ok and bool(workers)
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthStatus(
        status="ok" if healthy else "degraded",
        service=f"{settings.app_name}-worker",
        version="1.0.0",
        environment=settings.environment,
        dependencies=dependencies,
    )


async def _broker_health(settings: Settings) -> tuple[bool, list[str]]:
    """Whether the broker answers, and which workers are consuming.

    Both checks are bounded and run off the event loop: `inspect.ping` waits on
    a reply from every worker, and a health endpoint that blocks on a busy
    worker is a health endpoint that reports an outage it caused.
    """
    if not settings.broker_url:
        return False, []

    def probe() -> tuple[bool, list[str]]:
        try:
            from app.tasks.celery_app import celery_app

            connection = celery_app.connection()
            try:
                connection.ensure_connection(max_retries=1, timeout=3)
            finally:
                connection.release()

            replies = celery_app.control.inspect(timeout=2).ping() or {}
            return True, list(replies)
        except Exception as exc:
            logger.warning("worker health check failed", extra={"err": str(exc)})
            return False, []

    return await asyncio.to_thread(probe)
