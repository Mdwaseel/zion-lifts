"""The document lifecycle, and the rules about moving through it.

Kept in its own module, away from the models, because these rules are the part
worth reading on their own: a document's status is the only thing telling an
operator whether an answer citing it is current, and a status set by assignment
somewhere in a view is a status nobody can reason about.

The transition table is the whole specification. ``check`` is the only way to
ask whether a move is legal, and ``Document.transition_to`` is the only way to
make one.
"""

from __future__ import annotations

from django.db import models


class DocumentState(models.TextChoices):
    """Where a document is in its journey from upload to answerable.

    The middle five are the stages of one ingestion run. They are separate
    states rather than a progress percentage because they are what an operator
    reads when something has been stuck for ten minutes: "EMBEDDING" says which
    dependency to go and look at, where "PROCESSING, 40%" does not.
    """

    UPLOADED = "uploaded", "Uploaded"
    PROCESSING = "processing", "Processing"
    EXTRACTING = "extracting", "Extracting text"
    CHUNKING = "chunking", "Chunking"
    EMBEDDING = "embedding", "Embedding"
    INDEXING = "indexing", "Indexing"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"
    DELETING = "deleting", "Deleting"
    DELETED = "deleted", "Deleted"


# Stages that mean work is in flight. A job may be running; the vector index for
# this version is incomplete and must not be searched.
IN_FLIGHT = frozenset(
    {
        DocumentState.PROCESSING,
        DocumentState.EXTRACTING,
        DocumentState.CHUNKING,
        DocumentState.EMBEDDING,
        DocumentState.INDEXING,
    }
)

# States from which nothing further happens without a new instruction.
TERMINAL = frozenset({DocumentState.READY, DocumentState.FAILED, DocumentState.DELETED})

_S = DocumentState

# Every legal move. Anything absent is rejected — including a state to itself,
# so a duplicated task delivery cannot quietly re-enter a stage it is already in
# and reset the clock on it.
TRANSITIONS: dict[str, frozenset[str]] = {
    _S.UPLOADED: frozenset({_S.PROCESSING, _S.DELETING, _S.FAILED}),
    # PROCESSING -> READY is the one shortcut in the table, and it exists
    # because a Document and a DocumentVersion share this vocabulary while
    # moving at different rates. The version really is extracted, then chunked,
    # then embedded, then indexed, and it walks every stage. The document is a
    # *summary* of that: it is PROCESSING while an edition is in flight and
    # READY once one is live. Re-indexing a document that already has three
    # versions does not extract the document, so making it march through the
    # detailed stages a second time would be a fiction — and one that leaves it
    # stuck, because nothing reports those stages on its behalf.
    _S.PROCESSING: frozenset({_S.EXTRACTING, _S.READY, _S.FAILED, _S.DELETING}),
    _S.EXTRACTING: frozenset({_S.CHUNKING, _S.FAILED, _S.DELETING}),
    _S.CHUNKING: frozenset({_S.EMBEDDING, _S.FAILED, _S.DELETING}),
    _S.EMBEDDING: frozenset({_S.INDEXING, _S.FAILED, _S.DELETING}),
    _S.INDEXING: frozenset({_S.READY, _S.FAILED, _S.DELETING}),
    # Reindex sends a finished document back to the start of the same path.
    _S.READY: frozenset({_S.PROCESSING, _S.DELETING}),
    # Retry does the same for a failed one.
    _S.FAILED: frozenset({_S.PROCESSING, _S.DELETING}),
    # Deletion is its own short lifecycle: a document being removed from the
    # index cannot slip back into the ingestion path, only forward or back out
    # to FAILED if the removal itself breaks.
    _S.DELETING: frozenset({_S.DELETED, _S.FAILED}),
    _S.DELETED: frozenset(),
}

# The stages an ingestion run walks, in order. Used to derive progress without
# a second source of truth about what the sequence is.
INGESTION_SEQUENCE: tuple[str, ...] = (
    _S.PROCESSING,
    _S.EXTRACTING,
    _S.CHUNKING,
    _S.EMBEDDING,
    _S.INDEXING,
    _S.READY,
)


class InvalidTransition(Exception):
    """A move the lifecycle does not allow.

    Raised rather than logged: an unexpected transition means two things
    disagree about where a document is, and continuing from that would leave
    the index and the records describing it out of step.
    """

    def __init__(self, current: str, target: str) -> None:
        # Coerced to plain strings: these arrive as either a TextChoices member
        # or the raw value out of the database, and an operator reading the log
        # wants "ready", not "DocumentState.READY".
        self.current = str(current)
        self.target = str(target)
        allowed = sorted(str(s) for s in TRANSITIONS.get(current, frozenset()))
        super().__init__(
            f"Cannot move a document from '{self.current}' to '{self.target}'. "
            f"Allowed from '{self.current}': {', '.join(allowed) or 'nothing'}."
        )


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


def check(current: str, target: str) -> None:
    """Raise :class:`InvalidTransition` unless the move is allowed."""
    if not can_transition(current, target):
        raise InvalidTransition(current, target)


def progress_for(state: str) -> int:
    """Whole-percent progress implied by a stage, 0-100.

    Derived from the sequence rather than stored, so the two cannot disagree.
    Stages are evenly spaced on purpose: the real durations depend entirely on
    document size and provider latency, and a weighting tuned for one PDF would
    mislead on the next.
    """
    if state == DocumentState.READY:
        return 100
    if state not in INGESTION_SEQUENCE:
        return 0
    index = INGESTION_SEQUENCE.index(state)
    return round(index * 100 / (len(INGESTION_SEQUENCE) - 1))
