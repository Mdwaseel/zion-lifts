"""FastAPI application factory."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import Container
from app.api.routes import chat, documents, health, internal
from app.api.schemas.common import ErrorDetail, ErrorResponse
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger, new_request_id, set_request_id
from app.llm.base import LLMError
from app.llm.fallback import AllProvidersFailedError

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

DESCRIPTION = """Retrieval-augmented question answering over your own documents.

- **Ingest** PDFs, web pages and raw text into a Qdrant collection.
- **Retrieve** with hybrid dense + BM25 search, fused by RRF and cross-encoder reranked.
- **Answer** with citations, a confidence score, and automatic provider fallback.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    logger.info("starting up", extra={"env": settings.environment})

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

    return app


def _register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Attach a correlation id to every log line and response."""
        request_id = request.headers.get(REQUEST_ID_HEADER) or new_request_id()
        set_request_id(request_id)
        started = time.perf_counter()

        response = await call_next(request)

        took_ms = (time.perf_counter() - started) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["X-Response-Time-ms"] = f"{took_ms:.1f}"
        logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={"took_ms": round(took_ms, 1)},
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
    async def on_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error(
            "validation_error",
            "; ".join(
                f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in exc.errors()
            )
            or "Invalid request.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(AllProvidersFailedError)
    async def on_providers_failed(
        request: Request, exc: AllProvidersFailedError
    ) -> JSONResponse:
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
