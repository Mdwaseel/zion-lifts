"""FastAPI application factory."""

from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import Container
from app.api.routes import chat, documents, health, internal, ops
from app.api.schemas.common import ErrorDetail, ErrorResponse
from app.core import events
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger, new_request_id, set_request_id
from app.core.metrics import configure_metrics, metrics
from app.llm.base import LLMError
from app.llm.fallback import AllProvidersFailedError

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

# A correlation id is echoed into every log line this process writes, so an
# inbound one is accepted only when it looks like an id. Without this a caller
# could inject newlines and forge log entries, or hand us a megabyte of header
# that is then copied onto thousands of lines.
_ID_SHAPE = re.compile(r"^[A-Za-z0-9._-]+$")


def resolve_request_id(raw: str | None, max_length: int) -> str:
    """The caller's id if it is usable, otherwise a fresh one."""
    if raw and len(raw) <= max_length and _ID_SHAPE.match(raw):
        return raw
    return new_request_id()


DESCRIPTION = """Retrieval-augmented question answering over your own documents.

- **Ingest** PDFs, web pages and raw text into a Qdrant collection.
- **Retrieve** with hybrid dense + BM25 search, fused by RRF and cross-encoder reranked.
- **Answer** with citations, a confidence score, and automatic provider fallback.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    configure_logging(
        settings.log_level,
        settings.log_json,
        service=settings.app_name,
        environment=str(settings.environment),
    )
    configure_metrics(settings.metrics_enabled)
    logger.info("starting up", extra={"event": "service_started", "env": settings.environment})

    # A container may already be installed by tests; only build (and tear down)
    # the object graph when we are the ones who own it.
    owns_container = getattr(app.state, "container", None) is None
    if owns_container:
        app.state.container = await Container.build(settings)

    try:
        yield
    finally:
        logger.info("shutting down")
        if owns_container:
            await app.state.container.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Service",
        description=DESCRIPTION,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_prod else None,
        redoc_url="/redoc" if not settings.is_prod else None,
        openapi_url="/openapi.json" if not settings.is_prod else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    _register_middleware(app)
    _register_exception_handlers(app)

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(chat.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(internal.router, prefix=settings.api_prefix)
    app.include_router(ops.router, prefix=settings.api_prefix)

    return app


def _route_of(request: Request) -> str:
    """The route template, never the concrete path.

    `/documents/{document_id}` rather than `/documents/8f2c...`. The concrete
    path carries an identifier, and an identifier in a metric label is a new
    time series per document — so the template is what gets labelled, and the
    real path stays in the log line where it belongs.
    """
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if template:
        return str(template)
    return "unmatched"


def _register_middleware(app: FastAPI) -> None:
    settings = get_settings()
    header = settings.request_id_header or REQUEST_ID_HEADER
    max_id = settings.request_id_max_length

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        """Correlation id, timing, and one completion record per request."""
        request_id = resolve_request_id(request.headers.get(header), max_id)
        set_request_id(request_id)
        started = time.perf_counter()
        method = request.method

        try:
            response = await call_next(request)
        except Exception:
            took_ms = (time.perf_counter() - started) * 1000
            route = _route_of(request)
            # The handler chain has already logged the exception with its
            # traceback; this records that the *request* ended badly, which is
            # what the latency and error-rate numbers are counted from.
            logger.warning(
                events.REQUEST_FAILED,
                extra={
                    "event": events.REQUEST_FAILED,
                    "method": method,
                    "route": route,
                    "duration_ms": round(took_ms, 1),
                },
            )
            metrics.increment("http_requests_total", endpoint=route, method=method, status="error")
            metrics.observe("http_request_duration", took_ms, endpoint=route, status="error")
            raise

        took_ms = (time.perf_counter() - started) * 1000
        route = _route_of(request)
        response.headers[header] = request_id
        response.headers["X-Response-Time-ms"] = f"{took_ms:.1f}"

        # Bucketed rather than exact: 2xx/4xx/5xx is what an alert is written
        # against, and the exact code stays in the log line.
        status_class = f"{response.status_code // 100}xx"
        metrics.increment("http_requests_total", endpoint=route, method=method, status=status_class)
        metrics.observe("http_request_duration", took_ms, endpoint=route, status=status_class)

        logger.info(
            events.REQUEST_COMPLETED,
            extra={
                "event": events.REQUEST_COMPLETED,
                "method": method,
                # The template, and the real path separately — the query string
                # is never logged, because it is where a caller puts anything.
                "route": route,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(took_ms, 1),
            },
        )
        return response


def _error(code: str, message: str, status_code: int) -> JSONResponse:
    from app.core.logging import get_request_id

    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=message, request_id=get_request_id())
        ).model_dump(),
    )


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(
            "validation_error",
            "; ".join(f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors())
            or "Invalid request.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(AllProvidersFailedError)
    async def on_providers_failed(request: Request, exc: AllProvidersFailedError) -> JSONResponse:
        logger.error("all providers failed", extra={"errors": exc.errors})
        return _error(
            "llm_unavailable",
            "No language model provider is currently available.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @app.exception_handler(LLMError)
    async def on_llm_error(request: Request, exc: LLMError) -> JSONResponse:
        return _error("llm_error", str(exc), status.HTTP_502_BAD_GATEWAY)

    @app.exception_handler(Exception)
    async def on_unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error", extra={"path": request.url.path})
        return _error(
            "internal_error",
            "An unexpected error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


app = create_app()
