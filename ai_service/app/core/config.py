"""Typed application settings loaded from environment / .env.

Two things here are load-bearing and easy to get wrong again, so they are
called out rather than left to be rediscovered:

*Comma-separated lists need ``NoDecode``.* pydantic-settings JSON-decodes every
complex-typed field as it reads it from the environment, and that happens before
any validator on the model runs. Without ``NoDecode`` a ``field_validator`` that
splits ``"a,b,c"`` never gets the chance — the source raises ``SettingsError``
first, and the service cannot start at all. ``NoDecode`` hands the raw string
through to validation, which is where the splitting belongs.

*There are no nested settings models, so there is no ``__`` delimiter.* An
earlier ``.env`` wrote ``QDRANT__URL`` and ``GEMINI__API_KEY``, which bound to
nothing and were dropped in silence: Qdrant fell back to localhost and every LLM
provider came up without a key. ``_reject_nested_names`` now makes that an error
instead of a mystery.
"""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core import constants
from app.core.exceptions import ConfigurationError


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_deployed(self) -> bool:
        """Staging is held to production's standards on purpose — a staging
        environment configured more loosely than production does not rehearse
        production."""
        return self in {Environment.STAGING, Environment.PRODUCTION}


# The names this project used before the four above. Accepted so an existing
# .env keeps working rather than failing on a word.
_ENVIRONMENT_ALIASES = {
    "local": Environment.DEVELOPMENT,
    "dev": Environment.DEVELOPMENT,
    "develop": Environment.DEVELOPMENT,
    "prod": Environment.PRODUCTION,
    "stage": Environment.STAGING,
    "testing": Environment.TEST,
}

# `list[str]` read from a comma-separated environment variable. See the module
# docstring for why the annotation is required.
CsvList = Annotated[list[str], NoDecode]

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal")

# Every provider that can answer, and the field holding its credential.
_PROVIDER_KEYS = {
    "gemini": "gemini_api_key",
    "groq": "groq_api_key",
    "openai": "openai_api_key",
}


def _is_local(url: str) -> bool:
    return any(host in url for host in _LOCAL_HOSTS)


def _dotenv_keys(env_file: object) -> set[str]:
    """The variable names a .env file sets, without evaluating any of them.

    Only used to spot names that will be ignored, so it does not need to be a
    full parser — and deliberately never touches the values, which are secrets.
    """
    if not env_file or not isinstance(env_file, str | os.PathLike):
        return set()
    try:
        with open(env_file, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return set()

    keys = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name = stripped.split("=", 1)[0].strip()
        keys.add(name.removeprefix("export ").strip())
    return keys


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App -----------------------------------------------------------------
    app_name: str = constants.SERVICE_NAME
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False

    # --- Observability -------------------------------------------------------
    # Metrics are in-process counters and histograms; disabling them makes every
    # record a no-op rather than removing the call sites.
    metrics_enabled: bool = True
    # The header a correlation id arrives on and is echoed back in. Configurable
    # because the value has to match whatever the proxy in front already sets.
    request_id_header: str = "X-Request-ID"
    # An inbound id is echoed into every log line, so it is accepted only if it
    # looks like an id. Anything longer or stranger is replaced with a generated
    # one rather than trusted — a header is caller-controlled input.
    request_id_max_length: int = Field(default=64, ge=8, le=200)
    # How long a job may sit in flight before an operator should look at it.
    # Detection only: nothing is failed automatically on this signal.
    ingestion_stale_after_seconds: int = Field(default=1800, ge=60)

    # --- Security ------------------------------------------------------------
    # Empty disables API-key auth, which is convenient locally and refused in a
    # deployed environment by the validator below.
    api_keys: CsvList = Field(default_factory=list)
    internal_token: str = "change-me"
    cors_origins: CsvList = Field(default_factory=lambda: ["*"])

    # --- Vector store --------------------------------------------------------
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    # The collection for content indexed before knowledge bases existed. New
    # collections are named by app.vectorstore.collections.CollectionNameBuilder.
    qdrant_collection: str = constants.DEFAULT_COLLECTION
    qdrant_timeout: float = 30.0

    # --- Broker --------------------------------------------------------------
    # Celery's broker, shared with the Django side: both must point at the same
    # Redis or the worker consumes an empty queue while uploads pile up in
    # another one.
    redis_url: str | None = None
    # Only set these to split broker and results across instances. Left unset
    # they follow redis_url, which is the arrangement this project deploys.
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_queue: str = "ai_ingestion"

    # One process at a time by default, and deliberately. Each worker child
    # loads its own copy of the embedding model and the cross-encoder; four of
    # them is four times the resident memory for throughput that is bounded by
    # the same CPU either way. Raise it only after measuring resident set size
    # under real documents.
    celery_worker_concurrency: int = Field(default=1, ge=1, le=32)
    celery_worker_prefetch_multiplier: int = Field(default=1, ge=1, le=16)
    # A large scanned PDF is minutes of embedding, not seconds. The soft limit
    # raises an exception the pipeline can report; the hard limit kills the
    # child, so it sits well above it.
    celery_task_soft_time_limit: int = Field(default=1500, ge=30)
    celery_task_time_limit: int = Field(default=1800, ge=60)
    celery_task_max_retries: int = Field(default=3, ge=0, le=10)
    celery_retry_backoff: int = Field(default=30, ge=1)
    celery_retry_backoff_max: int = Field(default=600, ge=1)

    # --- Document storage ----------------------------------------------------
    # How the worker turns a `file_reference` into bytes. "http" asks the
    # backend for it over an authenticated internal route and assumes nothing
    # about where the worker runs; "local" reads a shared volume and is faster
    # but only correct when both containers really do mount the same one.
    document_storage: Literal["http", "local"] = "http"
    # For document_storage=local: the directory Django's MEDIA_ROOT is mounted
    # at inside this container. Every reference is resolved beneath it and a
    # path that escapes it is refused.
    document_storage_root: str | None = None

    # --- Backend callback ----------------------------------------------------
    # Where the worker reports stage transitions. Without it a run does its work
    # and tells nobody, so the deployment guard requires it.
    backend_url: str | None = None
    # Shared secret for the internal routes in both directions. Never a user
    # token, never in a URL, never logged.
    ai_service_internal_token: str | None = None
    backend_timeout: float = Field(default=15.0, gt=0)
    # The callback is retried in-process before the whole task is retried: a
    # one-second blip should not cost a re-embedding.
    backend_retries: int = Field(default=3, ge=0, le=10)

    # --- Embeddings ----------------------------------------------------------
    # Where the vectors come from. "api" calls the Hugging Face Serverless
    # Inference API and needs no torch in the image; "local" loads
    # sentence-transformers in-process. "auto" picks the API when a token is
    # set, which is what makes an image without torch work by simply having
    # HF_API_TOKEN in the environment.
    embedding_provider: Literal["auto", "api", "local"] = "auto"
    # Read access to the model on huggingface.co. Required by the API provider,
    # ignored by the local one. Never logged.
    hf_api_token: str | None = None
    hf_api_base: str = "https://router.huggingface.co/hf-inference/models"
    hf_api_timeout: float = Field(default=30.0, gt=0)
    # A cold serverless model answers 503 for up to a minute after a quiet
    # period, so the first call of the day is retried rather than failed.
    hf_api_max_retries: int = Field(default=3, ge=0, le=10)
    hf_api_backoff: float = Field(default=1.0, gt=0)

    # The model everything is indexed and queried with. HF_EMBEDDING_MODEL is
    # accepted as well as EMBEDDING_MODEL so an .env written for the API
    # provider binds to the same field instead of a second one that would
    # silently disagree with it.
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias=AliasChoices("embedding_model", "hf_embedding_model"),
    )
    # Used only when the primary cannot answer, and only for *indexing*. Its
    # vectors go to their own collection, named after it — see
    # app/embeddings/router.py for why they must never share one. Leave unset to
    # have an embedding failure fail the run instead.
    embedding_fallback_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("embedding_fallback_model", "hf_fallback_embedding_model"),
    )
    # Bumped by hand when the same model name starts producing different
    # vectors — a weights revision, a different pooling setting. It is part of
    # the collection name, so a bump routes new writes to a new collection
    # instead of poisoning the old one.
    embedding_model_version: str = "v1"
    embedding_dim: int = 384
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    embedding_cache_size: int = 4096

    # --- Reranking -----------------------------------------------------------
    reranker_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Chunking ------------------------------------------------------------
    chunk_size: int = constants.DEFAULT_CHUNK_SIZE
    chunk_overlap: int = constants.DEFAULT_CHUNK_OVERLAP

    # --- Retrieval -----------------------------------------------------------
    # The defaults reproduce exactly what the pipeline did when these numbers
    # were constants: each retriever fetched top_k * 4 * 4 = 80 candidates, RRF
    # returned 20 of them, and the reranker cut that to 5.
    dense_top_k: int = Field(default=80, ge=1, le=1000)
    sparse_top_k: int = Field(default=80, ge=1, le=1000)
    fusion_top_k: int = Field(default=20, ge=1, le=500)
    rerank_top_k: int = Field(default=constants.DEFAULT_TOP_K, ge=1, le=50)

    hybrid_alpha: float = Field(default=0.5, ge=0.0, le=1.0)  # 1.0 dense, 0.0 lexical
    query_rewrite_enabled: bool = True
    # RRF's smoothing constant. Larger flattens the difference between ranks;
    # 60 is the value from the original paper and what this pipeline shipped
    # with. Configurable so retrieval modes can be compared, not so it can be
    # nudged until a demo looks better.
    rrf_k: int = Field(default=constants.RRF_K, ge=1, le=1000)
    # Distinct terms one chunk may contribute to its lexical vector. A word list
    # or an index page would otherwise produce a vector too dense to rank with.
    sparse_max_terms: int = Field(default=512, ge=16, le=8192)

    # --- Grounding thresholds ------------------------------------------------
    # 0.0 keeps the historical behaviour: nothing was filtered by raw score, and
    # answerability was decided by the confidence bands alone.
    min_retrieval_score: float = Field(default=0.0, ge=0.0, le=1.0)
    min_rerank_score: float = Field(default=0.0, ge=0.0, le=1.0)
    min_context_documents: int = Field(default=1, ge=0)
    confidence_high: float = Field(default=0.75, ge=0.0, le=1.0)
    confidence_low: float = Field(default=0.35, ge=0.0, le=1.0)

    # A token budget rather than a character one, because that is the limit the
    # model actually has. Converted at CHARS_PER_TOKEN; the default is the
    # 12,000-character budget this pipeline has always used.
    max_context_tokens: int = Field(default=3000, ge=256, le=200_000)

    # --- LLM -----------------------------------------------------------------
    llm_provider_order: CsvList = Field(default_factory=lambda: ["gemini", "groq", "openai"])
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    llm_timeout: float = 45.0

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    # --- Circuit breaker -----------------------------------------------------
    breaker_fail_threshold: int = 3
    breaker_reset_seconds: float = 60.0

    # --- Uploads / indexing --------------------------------------------------
    max_upload_bytes: int = constants.MAX_UPLOAD_BYTES
    # Points per Qdrant upsert. One request per vector would spend the whole
    # ingestion in round trips; too large a batch makes a single retry expensive
    # and can exceed the payload limit on a hosted cluster.
    vector_upsert_batch_size: int = Field(default=128, ge=1, le=2000)
    # Texts per embedding call. Separate from the batch above because the
    # constraint is different — model memory rather than request size.
    embed_batch_size: int = Field(default=64, ge=1, le=512)

    # --- parsing -------------------------------------------------------------
    @field_validator("api_keys", "cors_origins", "llm_provider_order", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        """Accept `A,B,C` as well as a real list. JSON is not special-cased:
        with NoDecode the source no longer tries it, and one syntax is easier to
        document than two."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("embedding_model", "embedding_fallback_model", "reranker_model")
    @classmethod
    def _model_id_is_clean(cls, v: str | None) -> str | None:
        """Refuse a model name carrying anything but a model name.

        `.env` values are not always comment-stripped: a line written

            HF_EMBEDDING_MODEL=some/model  # the primary

        can arrive with " # the primary" still attached. The name then goes
        straight into a request URL, the provider answers 400, and the message
        blames the model rather than the file it came from — while the same
        string is also feeding the collection name. Caught here, it is one line
        at boot naming the variable to go and fix.
        """
        if v is None:
            return v
        cleaned = v.strip()
        if not cleaned:
            return cleaned
        if any(ch.isspace() for ch in cleaned) or "#" in cleaned:
            raise ValueError(
                f"{cleaned!r} is not a model id — it contains whitespace or a '#'. "
                "An inline comment in .env is not always stripped; put the comment "
                "on its own line."
            )
        return cleaned

    @field_validator("environment", mode="before")
    @classmethod
    def _canonical_environment(cls, v: object) -> object:
        if isinstance(v, str):
            return _ENVIRONMENT_ALIASES.get(v.strip().lower(), v.strip().lower())
        return v

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_fits(cls, v: int, info) -> int:
        size = info.data.get("chunk_size")
        if size is not None and v >= size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return v

    # --- guards --------------------------------------------------------------
    @model_validator(mode="after")
    def _reject_nested_names(self) -> Settings:
        """Refuse to start when a `SECTION__FIELD` name is set anywhere.

        This settings model is flat. A variable like ``QDRANT__URL`` looks
        deliberate, matches no field, and is dropped without a word — which is
        exactly how this service once ran against localhost with no LLM key
        while its .env appeared fully populated.

        Both sources are checked, because the .env file is where it happened.
        """
        fields = type(self).model_fields
        candidates = set(os.environ) | _dotenv_keys(self.model_config.get("env_file"))

        offenders = sorted(
            name
            for name in candidates
            if "__" in name and name.replace("__", "_").lower() in fields
        )
        if offenders:
            raise ConfigurationError(
                [
                    f"{name} uses a nested name and is being ignored; this settings "
                    f"model is flat — write {name.replace('__', '_')} instead"
                    for name in offenders
                ]
            )
        return self

    @model_validator(mode="after")
    def _embedding_provider_is_usable(self) -> Settings:
        """An API embedding provider without a token cannot embed anything.

        Checked in every environment, not just deployed ones: the failure it
        prevents is a container that starts, accepts an upload, and only then
        discovers it has no way to turn text into vectors.
        """
        if self.embedding_provider == "api" and not self.hf_api_token:
            raise ConfigurationError(
                [
                    "EMBEDDING_PROVIDER=api requires HF_API_TOKEN; set the token, or "
                    "use EMBEDDING_PROVIDER=local to embed in-process (which needs "
                    "sentence-transformers installed)"
                ]
            )
        return self

    @model_validator(mode="after")
    def _deployment_requirements(self) -> Settings:
        """Everything a staging or production deployment must state explicitly.

        Development keeps its convenient defaults; a deployed environment gets
        none of them. Each check below exists because its default is not merely
        inconvenient in production but wrong: an unset API key list disables
        authentication outright, and a localhost Qdrant URL means the service
        starts happily and answers from an empty index.
        """
        if not self.environment.is_deployed:
            return self

        where = self.environment.value
        problems: list[str] = []

        if not self.qdrant_url or _is_local(self.qdrant_url):
            problems.append(
                f"QDRANT_URL must name a real host in {where} (got {self.qdrant_url!r})"
            )
        if not self.qdrant_api_key:
            problems.append(f"QDRANT_API_KEY is required in {where}")
        if not self.redis_url:
            problems.append(f"REDIS_URL is required in {where}")
        elif _is_local(self.redis_url):
            problems.append(f"REDIS_URL must name a real host in {where}")

        if not self.api_keys:
            problems.append(
                f"API_KEYS is required in {where}: an empty list disables API-key "
                "authentication on every public route"
            )
        if self.internal_token == "change-me" or len(self.internal_token) < 32:
            problems.append(
                f"INTERNAL_TOKEN must be a real value of at least 32 characters in {where}"
            )
        if "*" in self.cors_origins:
            problems.append(f"CORS_ORIGINS must name the real front-end origins in {where}")
        if self.debug:
            problems.append(f"DEBUG must be false in {where}")

        configured = [p for p in self.llm_provider_order if getattr(self, _PROVIDER_KEYS[p], None)]
        if not configured:
            wanted = ", ".join(_PROVIDER_KEYS[p].upper() for p in self.llm_provider_order)
            problems.append(
                f"at least one LLM credential is required in {where}; "
                f"LLM_PROVIDER_ORDER asks for {wanted}"
            )

        # The worker half. A deployment missing these ingests nothing and says
        # nothing about it, which is the failure worth catching at boot.
        if not self.backend_url:
            problems.append(f"BACKEND_URL is required in {where} for ingestion callbacks")
        if not self.ai_service_internal_token:
            problems.append(f"AI_SERVICE_INTERNAL_TOKEN is required in {where}")
        elif len(self.ai_service_internal_token) < 32:
            problems.append(f"AI_SERVICE_INTERNAL_TOKEN must be at least 32 characters in {where}")
        if self.document_storage == "local" and not self.document_storage_root:
            problems.append(
                "DOCUMENT_STORAGE_ROOT is required when DOCUMENT_STORAGE=local; "
                "the worker cannot resolve a file reference without it"
            )

        if problems:
            raise ConfigurationError(problems)
        return self

    @field_validator("llm_provider_order")
    @classmethod
    def _known_providers(cls, v: list[str]) -> list[str]:
        unknown = [p for p in v if p not in _PROVIDER_KEYS]
        if unknown:
            raise ValueError(
                f"unknown LLM provider(s): {', '.join(unknown)}; "
                f"choose from {', '.join(_PROVIDER_KEYS)}"
            )
        return v

    # --- derived -------------------------------------------------------------
    @property
    def is_prod(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def broker_url(self) -> str | None:
        """The broker, falling back to the Redis both services share."""
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str | None:
        return self.celery_result_backend or self.redis_url

    @property
    def max_context_chars(self) -> int:
        """The token budget as the character budget the context builder counts in."""
        return self.max_context_tokens * constants.CHARS_PER_TOKEN

    @property
    def configured_providers(self) -> list[str]:
        """Providers in preference order that actually hold a credential."""
        return [p for p in self.llm_provider_order if getattr(self, _PROVIDER_KEYS[p], None)]

    @property
    def embeddings_use_api(self) -> bool:
        """Whether vectors come from the Hugging Face API rather than in-process.

        "auto" resolves on the presence of a token, which is what lets an image
        built without torch work by setting HF_API_TOKEN and nothing else.
        """
        if self.embedding_provider == "api":
            return True
        if self.embedding_provider == "local":
            return False
        return bool(self.hf_api_token)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
