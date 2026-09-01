"""Everything between a routed question and a finished answer.

    evidence.py            what was gathered, numbered once, with its origin
    source_orchestrator.py  running the plan's sources, concurrently
    confidence.py           how well the evidence supports an answer
    answer_strategy.py      what to do about it, and the prompt that says so
    references.py           citations, verified links, follow-ups
    assistant.py            the sequence, the timing, and the log line

The split is not decorative. The answer policy — never claim Zion does X
without a source — is enforced by three of these together: ``evidence`` keeps
the origin of every passage, ``answer_strategy`` refuses to build a company
answer without one, and ``references`` refuses to attach a citation that does
not resolve. No single module can be edited into letting an unsourced claim
through.
"""

from __future__ import annotations

from app.orchestration.answer_strategy import AnswerPlan, Behaviour
from app.orchestration.assistant import AssistantPipeline, AssistantResult
from app.orchestration.confidence import ConfidenceComponents, EvidenceConfidence
from app.orchestration.evidence import EvidenceBundle, EvidenceItem, EvidenceKind
from app.orchestration.references import ResolvedReferences
from app.orchestration.source_orchestrator import SourceOrchestrator

__all__ = [
    "AnswerPlan",
    "AssistantPipeline",
    "AssistantResult",
    "Behaviour",
    "ConfidenceComponents",
    "EvidenceBundle",
    "EvidenceConfidence",
    "EvidenceItem",
    "EvidenceKind",
    "ResolvedReferences",
    "SourceOrchestrator",
]
