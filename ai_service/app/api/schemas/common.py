"""Shared response envelopes and primitives."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ErrorDetail(BaseSchema):
    code: str = Field(description="Machine-readable error code.")
    message: str
    request_id: str | None = None


class ErrorResponse(BaseSchema):
    error: ErrorDetail


class PageMeta(BaseSchema):
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + self.limit < self.total


class Page(BaseSchema, Generic[T]):
    items: list[T]
    meta: PageMeta


class HealthStatus(BaseSchema):
    status: str
    service: str
    version: str
    environment: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dependencies: dict[str, str] = Field(default_factory=dict)
