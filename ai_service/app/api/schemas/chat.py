"""Request/response models for the chat API."""

from __future__ import annotations

from pydantic import Field, field_validator

from app.api.schemas.common import BaseSchema
from app.core.constants import MAX_HISTORY_TURNS, MAX_QUESTION_CHARS, ConfidenceLevel, Role


class Message(BaseSchema):
    role: Role
    content: str = Field(min_length=1)


class ChatRequest(BaseSchema):
    """What a caller may ask for.

    Deliberately absent: ``collection`` and ``filters``. Both used to be taken
    from here and passed to Qdrant unchanged, which made the index's own naming
    the access-control boundary — any caller could name any collection, or send
    a filter matching everything. The corpus is now decided server-side by a
    :class:`~app.retrieval.scope.RetrievalScope`, and the most a caller can do
    is *narrow* it with the two fields below, which are validated against what
    they are already allowed to see.
    """

    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    history: list[Message] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS * 2)
    session_id: str | None = None
    knowledge_base_id: str | None = Field(
        default=None,
        max_length=64,
        description="Which knowledge base to search. Falls back to the service default.",
    )
    document_ids: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Narrow the search to these documents, within the knowledge base above.",
    )
    top_k: int | None = Field(default=None, ge=1, le=50)
    stream: bool = False

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("question must not be blank")
        return cleaned


class Citation(BaseSchema):
    """One source behind a claim in the answer.

    ``type`` was added when website content became a second kind of evidence.
    It defaults to ``document`` so a client written against the earlier shape
    keeps working and simply ignores it; ``url`` is set only for website
    citations, and is always a route this service has verified.
    """

    marker: str = Field(description="Inline marker used in the answer, e.g. [1].")
    chunk_id: str
    document_id: str
    type: str = Field(default="document", description="document | website")
    title: str | None = None
    source: str | None = None
    url: str | None = Field(default=None, description="Set for website sources only.")
    snippet: str
    score: float


class RelatedPage(BaseSchema):
    """A page on the site worth visiting next.

    Never produced by the model. Every one of these is resolved from the website
    index and re-verified before it is serialised, so a URL here is a URL that
    exists — see :mod:`app.orchestration.references`.
    """

    title: str
    url: str
    section: str | None = None
    description: str | None = None


class Usage(BaseSchema):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ChatResponse(BaseSchema):
    """The answer contract.

    Everything below ``took_ms`` in the original shape is unchanged. The four
    fields after it were added with the routing layer and all have defaults, so
    an older client deserialises this response exactly as it did before.
    """

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    session_id: str | None = None
    provider: str | None = None
    model: str | None = None
    rewritten_query: str | None = None
    usage: Usage | None = None
    took_ms: float = 0.0

    intent: str | None = Field(default=None, description="How the question was routed.")
    related_pages: list[RelatedPage] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)


class StreamChunk(BaseSchema):
    """One server-sent event payload during streaming.

    The protocol is additive. ``delta``, ``citations``, ``done`` and ``error``
    behave exactly as before and still arrive in that order; ``metadata`` and
    ``related_pages`` are new types that a client written against the earlier
    protocol will not recognise and will skip, which is what the existing
    front-end reader already does with anything it does not know.
    """

    type: str = Field(description="metadata | delta | citations | related_pages | done | error")
    content: str | None = None
    citations: list[Citation] | None = None
    related_pages: list[RelatedPage] | None = None
    suggested_questions: list[str] | None = None
    intent: str | None = None
    confidence: float | None = None
    confidence_level: ConfidenceLevel | None = None
    error: str | None = None
