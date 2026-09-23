"""Operational readouts for this process.

Guarded by the internal token, not public. What these return — provider names,
failure rates, circuit state, queue depth — is a map of the system's weak points
at this moment, and the endpoint is the sort of thing that ends up quietly
proxied to the internet if it was never protected in the first place.

Everything here is read from memory. There is no database query and no call to a
dependency, because these are the endpoints an operator reaches for when the
system is already unwell: a diagnostic that hangs because Qdrant is hanging
tells them nothing they did not already suspect.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import Container, get_container
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.core.security import require_internal_token

logger = get_logger(__name__)

router = APIRouter(
    prefix="/ops",
    tags=["ops"],
    dependencies=[Depends(require_internal_token)],
)


@router.get("/metrics", summary="Counters, histograms and gauges for this process")
async def read_metrics() -> dict[str, Any]:
    """This process's metrics, as JSON.

    Per process, and the response says so: with several API workers and several
    Celery children each holds its own numbers, exactly as a Prometheus scrape
    would collect them separately. Summing across replicas is the collector's
    job, not this endpoint's.
    """
    return {"scope": "process", **metrics.snapshot()}


@router.get("/providers", summary="Which providers are answering, and which are not")
async def read_providers(
    settings: Settings = Depends(get_settings),
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    """Provider health without calling any of them.

    Deliberately makes no request to an LLM or an embedding endpoint. A
    diagnostic that spends a token to tell you a provider is up is a diagnostic
    nobody can afford to poll, and a health check must never perform inference.
    """
    embeddings = container.embeddings
    snapshot = metrics.snapshot()
    counters: dict[str, float] = snapshot["counters"]  # type: ignore[assignment]

    def total(prefix: str) -> float:
        return sum(v for k, v in counters.items() if k.split("{")[0] == prefix)

    embedding_requests = total("embedding_requests_total")
    llm_requests = total("llm_requests_total")

    return {
        "embedding": {
            # The model actually producing vectors right now, which is not
            # necessarily the configured one — see app/embeddings/router.py.
            "active_model": embeddings.model_name,
            "dimension": embeddings.dimension,
            "source": "api" if settings.embeddings_use_api else "local",
            "degraded": bool(getattr(embeddings, "is_degraded", False)),
            "fallback_events": getattr(embeddings, "fallback_events", 0),
            "fallback_rate": _rate(total("embedding_fallback_total"), embedding_requests),
            "failure_rate": _rate(total("embedding_failures_total"), embedding_requests),
        },
        "llm": {
            "configured": settings.configured_providers,
            "last_used": container.llm.last_used,
            "fallback_rate": _rate(total("llm_fallback_total"), llm_requests),
            "failure_rate": _rate(total("llm_errors_total"), llm_requests),
            # State only — never a provider's response body, which can echo the
            # prompt that was sent to it.
            "circuits": container.llm.breaker_states(),
        },
        "vector_store": {
            "operations": total("qdrant_operations_total"),
            "errors": total("qdrant_errors_total"),
            "timeouts": total("qdrant_timeouts_total"),
            "error_rate": _rate(
                total("qdrant_errors_total"),
                total("qdrant_operations_total") + total("qdrant_errors_total"),
            ),
        },
    }


def _rate(numerator: float, denominator: float) -> float:
    """A ratio, or 0.0 when nothing has happened yet.

    Zero rather than null for the no-traffic case: an alert reading "fallback
    rate above 10%" should not fire on a service that has served nothing.
    """
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)
