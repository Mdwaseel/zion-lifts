"""The Celery application the worker runs.

Kept apart from the FastAPI app on purpose. They share a codebase and share
nothing else: the API serves requests and never executes a task, the worker
executes tasks and never binds a port. Running one inside the other would give
a slow ingestion the power to make the site's chat endpoint unresponsive, and
would scale the two together when their limits are nothing alike.

Start it with::

    celery -A app.tasks.celery_app:celery_app worker -Q ai_ingestion --concurrency 1

Concurrency is 1 by default because each child process loads its own copy of the
embedding model and the cross-encoder. See ``celery_worker_concurrency`` in
``app.core.config`` before raising it.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def build_celery(settings: Settings | None = None) -> Celery:
    settings = settings or get_settings()
    broker = settings.broker_url

    if not broker:
        # A deployed worker with no broker would sit idle for ever while uploads
        # queue up somewhere it cannot see, so that fails at start. Locally it
        # falls back to an in-memory broker instead: the module has to stay
        # importable for the tests, which drive the tasks directly and never
        # send a message.
        if settings.environment.is_deployed:
            raise ConfigurationError(
                [
                    "REDIS_URL (or CELERY_BROKER_URL) is required to run the ingestion "
                    "worker; it must be the same Redis the Django side enqueues to"
                ]
            )
        logger.warning(
            "no broker configured — using an in-memory one. Set REDIS_URL to consume real work."
        )
        broker = "memory://"

    app = Celery("ai_service", broker=broker, backend=settings.result_backend)

    app.conf.update(
        # --- routing ---------------------------------------------------------
        # Django sends to this queue by name. Both sides name it in one place
        # each and they must agree; they are checked against each other in
        # tests/unit/test_tasks.py.
        task_default_queue=settings.celery_task_queue,
        task_routes={"ai_service.*": {"queue": settings.celery_task_queue}},
        # --- serialisation ---------------------------------------------------
        # JSON only. Pickle would let a message execute arbitrary code in the
        # worker, and the two services deliberately share no Python types.
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # --- delivery --------------------------------------------------------
        # Acknowledge after the task returns, not before. A worker killed
        # mid-ingestion then leaves the message on the queue for another worker
        # rather than dropping it — which is safe here because ingestion is
        # idempotent, and unsafe only for tasks that are not.
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        # One message at a time. With late acks and long tasks, prefetching
        # would park work on a busy worker while an idle one waits.
        worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
        worker_concurrency=settings.celery_worker_concurrency,
        # --- limits ----------------------------------------------------------
        # Soft first, so the pipeline gets an exception it can report; hard well
        # above it as the backstop that reclaims a wedged child.
        task_soft_time_limit=settings.celery_task_soft_time_limit,
        task_time_limit=settings.celery_task_time_limit,
        broker_connection_retry_on_startup=True,
        broker_transport_options={"visibility_timeout": settings.celery_task_time_limit + 60},
        result_expires=3600,
        timezone="UTC",
        enable_utc=True,
    )

    configure_logging(settings.log_level, settings.log_json)
    logger.info(
        "celery configured",
        extra={
            "queue": settings.celery_task_queue,
            "concurrency": settings.celery_worker_concurrency,
            "soft_time_limit": settings.celery_task_soft_time_limit,
        },
    )

    # Importing the module is what registers the tasks. Done here, after the app
    # exists, because the decorators bind to it.
    app.autodiscover_tasks(["app.tasks"], related_name="ingestion", force=True)
    from app.tasks import ingestion  # noqa: F401  (import for its side effect)

    return app


celery_app = build_celery()
