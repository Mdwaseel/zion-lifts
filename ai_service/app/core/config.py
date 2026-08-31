"""Typed application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core import constants


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App -----------------------------------------------------------------
    app_name: str = constants.SERVICE_NAME
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False

    # --- Security ------------------------------------------------------------
    api_keys: list[str] = Field(default_factory=list)
    internal_token: str = "change-me"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # --- Vector store --------------------------------------------------------
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = constants.DEFAULT_COLLECTION
    qdrant_timeout: float = 30.0

    # --- Embeddings ----------------------------------------------------------
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
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
    top_k: int = constants.DEFAULT_TOP_K
    hybrid_alpha: float = 0.5  # 1.0 = pure vector, 0.0 = pure keyword
    query_rewrite_enabled: bool = True

    # --- LLM -----------------------------------------------------------------
    llm_provider_order: list[str] = Field(default_factory=lambda: ["gemini", "groq", "openai"])
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

    @field_validator("api_keys", "cors_origins", "llm_provider_order", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        """Accept `A,B,C` from env vars as well as JSON lists."""
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                return v
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
