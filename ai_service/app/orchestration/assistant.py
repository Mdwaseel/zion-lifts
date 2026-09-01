"""The assistant pipeline: one question in, one answered question out.

    route  ──▶  gather  ──▶  score  ──▶  strategy  ──▶  generate  ──▶  resolve  ──▶  guard

Each arrow crosses a module boundary, and each of those modules can be tested
without the ones on either side. What lives *here* is only the sequence, the
timing and the one structured log line an operator reads afterwards — no
matching, no scoring, no prompt text.

Two decisions in this file are worth knowing about before reading it.

**A terminal route never reaches a model.** A refusal, a redirect and an
unverifiable company question are all answered with fixed text. That is not a
shortcut: text produced by the model is text the model can be argued out of, and
a refusal is precisely the moment when it will be.

**Streaming resolves citations from the accumulated answer, not from a promise.**
The markers are only known once the answer exists, so the ``citations`` and
``related_pages`` events arrive after the last ``delta``. The order is part of
the protocol, and the front end already reads it that way.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.api.schemas.chat import Citation, Message, RelatedPage
from app.core import events
from app.core.constants import ConfidenceLevel
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.llm.base import LLMUsage
from app.orchestration import answer_strategy, references
from app.orchestration import confidence as confidence_scoring
from app.orchestration.answer_strategy import AnswerPlan, Behaviour
from app.orchestration.confidence import EvidenceConfidence
from app.orchestration.evidence import EvidenceBundle
from app.orchestration.source_orchestrator import SourceOrchestrator, WebsiteSource
from app.query_router import QueryRouter, RouteDecision
from app.rag.pipeline import StageTimings
from app.retrieval.scope import RetrievalScope
from app.security import output_guard

logger = get_logger(__name__)


@dataclass(slots=True)
class AssistantResult:
    """Everything the API layer needs to build a response."""

    answer: str
    intent: str
    confidence: EvidenceConfidence
    citations: list[Citation] = field(default_factory=list)
    related_pages: list[RelatedPage] = field(default_factory=list)
    suggested_questions: list[str] = field(default_factory=list)
    behaviour: str = str(Behaviour.ANSWER)
    provider: str | None = None
    model: str | None = None
    usage: LLMUsage = field(default_factory=LLMUsage)
    rewritten_query: str | None = None
    bundle: EvidenceBundle = field(default_factory=EvidenceBundle)
    took_ms: float = 0.0
    timings: StageTimings = field(default_factory=StageTimings)

    @property
    def confidence_level(self) -> ConfidenceLevel:
        return self.confidence.level


class AssistantPipeline:
    """Composition of the routing, retrieval, generation and guard layers."""

    def __init__(
        self,
        router: QueryRouter,
        orchestrator: SourceOrchestrator,
        llm: object,
        website: WebsiteSource,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        max_context_chars: int = 12000,
        confidence_high: float = 0.70,
        confidence_low: float = 0.35,
    ) -> None:
        self._router = router
        self._orchestrator = orchestrator
        self._llm = llm
        self._website = website
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._max_context_chars = max_context_chars
        self._high = confidence_high
        self._low = confidence_low

    # --- shared front half ------------------------------------------------

    def _prepare(
        self, question: str, history: list[Message] | None, timings: StageTimings
    ) -> RouteDecision:
        mark = time.perf_counter()
        decision = self._router.route(question, history)
        timings.routing_ms = (time.perf_counter() - mark) * 1000
        metrics.increment("assistant_intent_total", intent=str(decision.intent))
        if decision.security.blocked:
            metrics.increment("assistant_blocked_total", threat=str(decision.security.kind))
        return decision

    async def _gather_and_plan(
        self,
        decision: RouteDecision,
        scope: RetrievalScope,
        history: list[Message] | None,
        top_k: int | None,
        timings: StageTimings,
    ) -> tuple[EvidenceBundle, EvidenceConfidence, AnswerPlan]:
        if answer_strategy.is_ambiguous(decision):
            # Decided before gathering. Retrieval cannot resolve "which lift is
            # best?", so running it would spend a vector search and a rerank on
            # evidence the clarifying question will not use.
            metrics.increment("assistant_behaviour_total", behaviour=str(Behaviour.CLARIFY))
            return (
                EvidenceBundle(),
                EvidenceConfidence(0.0, ConfidenceLevel.LOW, reason="question is ambiguous"),
                answer_strategy.clarify_plan(decision, history),
            )

        bundle = await self._orchestrator.gather(decision, scope, history, top_k, timings)

        mark = time.perf_counter()
        confidence = confidence_scoring.assess(
            decision.question, bundle, decision.intent, self._high, self._low
        )
        timings.grounding_ms = (time.perf_counter() - mark) * 1000

        plan = answer_strategy.build(decision, bundle, confidence, history, self._max_context_chars)
        metrics.increment("assistant_behaviour_total", behaviour=str(plan.behaviour))
        return bundle, confidence, plan

    def _terminal(
        self, decision: RouteDecision, timings: StageTimings, started: float
    ) -> AssistantResult:
        """The answer for a route that ended before retrieval."""
        reply = decision.reply
        assert reply is not None  # guaranteed by RouteDecision.is_terminal
        timings.total_ms = (time.perf_counter() - started) * 1000

        # A greeting and a refusal both end here, and they are not the same
        # event. Counting "hi" as a refusal makes chat_refusals_total track how
        # politely visitors open rather than where the corpus falls short, which
        # is the one thing that metric is watched for.
        conversational = decision.is_conversational
        if conversational:
            metrics.increment("chat_conversational_total", intent=str(decision.intent))
            metrics.observe("chat_duration", timings.total_ms, outcome="conversational")
            logger.info(
                "conversational answer",
                extra={
                    "event": "chat_conversational",
                    **decision.describe(),
                    **timings.as_log_fields(),
                },
            )
        else:
            metrics.increment("chat_refusals_total", mode="routed")
            metrics.observe("chat_duration", timings.total_ms, outcome="refused")
            logger.info(
                events.GROUNDING_REFUSED,
                extra={
                    "event": events.GROUNDING_REFUSED,
                    "reason": str(reply.threat),
                    **decision.describe(),
                    **timings.as_log_fields(),
                },
            )

        return AssistantResult(
            answer=reply.text,
            intent=str(reply.intent),
            confidence=EvidenceConfidence(
                # A written greeting is exactly as reliable as it looks: it made
                # no claim, so there is nothing for a confidence score to be
                # about. HIGH says "this answer is not a guess", not "well
                # evidenced" — and reporting a greeting as LOW confidence would
                # put a hedge on the UI beside "Hi!".
                1.0 if conversational else 0.0,
                ConfidenceLevel.HIGH if conversational else ConfidenceLevel.LOW,
                reason="conversational" if conversational else str(reply.threat),
            ),
            behaviour="conversational" if conversational else "refused",
            took_ms=timings.total_ms,
            timings=timings,
        )

    def _finish(
        self,
        raw_answer: str,
        decision: RouteDecision,
        bundle: EvidenceBundle,
        plan: AnswerPlan,
        confidence: EvidenceConfidence,
    ) -> tuple[str, references.ResolvedReferences, EvidenceConfidence]:
        """Guard the answer, resolve its references, and re-score it.

        Order matters. The output guard runs first because a leaked instruction
        replaces the whole answer and there is then nothing to cite; references
        are resolved from what survives; and confidence is finalised last,
        because whether the answer cited its sources is a component of it.
        """
        guarded = output_guard.guard(raw_answer)
        if guarded.replaced:
            metrics.increment("output_guard_replacements_total")
            logger.warning(
                "answer replaced by the output guard",
                extra={"event": "output_guard_tripped", "notes": ",".join(guarded.notes)},
            )
        elif guarded.redacted:
            metrics.increment("output_guard_redactions_total")

        resolved = references.resolve(
            guarded.text, decision, bundle, plan.cited_items, self._website.current
        )
        final_confidence = confidence_scoring.with_citation_support(
            confidence, len(resolved.citations), len(plan.cited_items), self._high, self._low
        )
        return guarded.text, resolved, final_confidence

    def _log_completion(
        self,
        decision: RouteDecision,
        bundle: EvidenceBundle,
        plan: AnswerPlan,
        resolved: references.ResolvedReferences,
        confidence: EvidenceConfidence,
        timings: StageTimings,
        provider: str | None,
        mode: str,
    ) -> None:
        """One line per answered question. Counts and identifiers only.

        Never the question, never the answer, never a passage. Everything an
        operator needs to explain a bad answer — how it was routed, what it
        found, how sure it was, which provider wrote it — without any of it
        being readable content.
        """
        logger.info(
            events.CHAT_COMPLETED,
            extra={
                "event": events.CHAT_COMPLETED,
                "mode": mode,
                "behaviour": str(plan.behaviour),
                "citations": len(resolved.citations),
                "related_pages": len(resolved.related_pages),
                "confidence": confidence.score,
                "confidence_level": str(confidence.level),
                "provider": provider,
                **confidence.components.as_fields(),
                **decision.describe(),
                **bundle.describe(),
                **timings.as_log_fields(),
            },
        )

    # --- unary ------------------------------------------------------------

    async def ask(
        self,
        question: str,
        scope: RetrievalScope,
        history: list[Message] | None = None,
        top_k: int | None = None,
    ) -> AssistantResult:
        started = time.perf_counter()
        timings = StageTimings()
        metrics.increment("chat_requests_total", mode="sync")

        decision = self._prepare(question, history, timings)
        if decision.is_terminal:
            return self._terminal(decision, timings, started)

        bundle, confidence, plan = await self._gather_and_plan(
            decision, scope, history, top_k, timings
        )

        if not plan.needs_model:
            timings.total_ms = (time.perf_counter() - started) * 1000
            resolved = references.resolve(
                plan.fixed_text or "", decision, bundle, plan.cited_items, self._website.current
            )
            self._log_completion(
                decision, bundle, plan, resolved, confidence, timings, None, "sync"
            )
            return AssistantResult(
                answer=resolved.answer,
                intent=str(decision.intent),
                confidence=confidence,
                related_pages=resolved.related_pages,
                suggested_questions=resolved.suggested_questions,
                behaviour=str(plan.behaviour),
                bundle=bundle,
                took_ms=timings.total_ms,
                timings=timings,
            )

        mark = time.perf_counter()
        try:
            result = await self._llm.complete(  # type: ignore[attr-defined]
                plan.messages, temperature=self._temperature, max_tokens=self._max_tokens
            )
        except Exception as exc:
            timings.total_ms = (time.perf_counter() - started) * 1000
            metrics.increment("chat_errors_total", mode="sync")
            metrics.observe("chat_duration", timings.total_ms, outcome="error")
            logger.warning(
                events.CHAT_FAILED,
                extra={
                    "event": events.CHAT_FAILED,
                    "error_type": type(exc).__name__,
                    **decision.describe(),
                    **timings.as_log_fields(),
                },
            )
            raise
        timings.llm_total_ms = (time.perf_counter() - mark) * 1000

        _, resolved, final_confidence = self._finish(
            result.text.strip(), decision, bundle, plan, confidence
        )
        timings.total_ms = (time.perf_counter() - started) * 1000

        metrics.increment("chat_success_total", mode="sync")
        metrics.observe("chat_duration", timings.total_ms, outcome="answered")
        metrics.observe("llm_duration", timings.llm_total_ms, provider=result.provider)
        metrics.increment("citations_generated_total", value=len(resolved.citations))
        self._log_completion(
            decision, bundle, plan, resolved, final_confidence, timings, result.provider, "sync"
        )

        return AssistantResult(
            answer=resolved.answer,
            intent=str(decision.intent),
            confidence=final_confidence,
            citations=resolved.citations,
            related_pages=resolved.related_pages,
            suggested_questions=resolved.suggested_questions,
            behaviour=str(plan.behaviour),
            provider=result.provider,
            model=result.model,
            usage=result.usage,
            rewritten_query=(
                decision.query.retrieval if decision.query.retrieval != question else None
            ),
            bundle=bundle,
            took_ms=timings.total_ms,
            timings=timings,
        )

    # --- streaming --------------------------------------------------------

    async def ask_stream(
        self,
        question: str,
        scope: RetrievalScope,
        history: list[Message] | None = None,
        top_k: int | None = None,
    ) -> AsyncIterator[tuple[str, object]]:
        """Yield ('metadata', dict), then ('delta', str)…, then the attachments.

        The metadata event goes out before the first token so the widget can
        render the intent and the confidence band while the answer is still
        arriving — the two things that tell a reader how to weigh what they are
        about to read.
        """
        started = time.perf_counter()
        timings = StageTimings()
        metrics.increment("chat_requests_total", mode="stream")
        logger.info(events.STREAM_STARTED, extra={"event": events.STREAM_STARTED})

        decision = self._prepare(question, history, timings)
        if decision.is_terminal:
            result = self._terminal(decision, timings, started)
            # Reported from the result rather than hardcoded low. It was a fair
            # constant while every terminal reply was a refusal; now a greeting
            # ends here too, and calling that low confidence puts "Weak match in
            # our documents (0% match)" underneath "Hi! 👋" — a disclaimer about
            # retrieval that never ran, attached to an answer that claimed
            # nothing.
            yield (
                "metadata",
                {
                    "intent": result.intent,
                    "confidence": result.confidence.score,
                    "level": str(result.confidence.level),
                },
            )
            yield "delta", result.answer
            yield "citations", []
            yield "done", None
            return

        bundle, confidence, plan = await self._gather_and_plan(
            decision, scope, history, top_k, timings
        )

        yield (
            "metadata",
            {
                "intent": str(decision.intent),
                "confidence": confidence.score,
                "level": str(confidence.level),
            },
        )

        if not plan.needs_model:
            timings.total_ms = (time.perf_counter() - started) * 1000
            resolved = references.resolve(
                plan.fixed_text or "", decision, bundle, plan.cited_items, self._website.current
            )
            self._log_completion(
                decision, bundle, plan, resolved, confidence, timings, None, "stream"
            )
            yield "delta", resolved.answer
            yield "citations", []
            if resolved.related_pages:
                yield "related_pages", resolved.related_pages
            yield "done", None
            return

        guard = output_guard.StreamGuard()
        llm_started = time.perf_counter()

        try:
            async for delta in self._llm.stream(  # type: ignore[attr-defined]
                plan.messages, temperature=self._temperature, max_tokens=self._max_tokens
            ):
                if not delta:
                    continue
                if timings.llm_time_to_first_token_ms is None:
                    timings.llm_time_to_first_token_ms = (time.perf_counter() - llm_started) * 1000
                    metrics.observe("llm_time_to_first_token", timings.llm_time_to_first_token_ms)
                safe = guard.feed(delta)
                if guard.tripped:
                    break
                if safe:
                    yield "delta", safe
        except GeneratorExit:
            timings.total_ms = (time.perf_counter() - started) * 1000
            metrics.increment("chat_stream_cancelled_total")
            logger.info(
                events.STREAM_CANCELLED,
                extra={"event": events.STREAM_CANCELLED, **timings.as_log_fields()},
            )
            raise
        except Exception as exc:
            timings.total_ms = (time.perf_counter() - started) * 1000
            metrics.increment("chat_errors_total", mode="stream")
            metrics.observe("chat_duration", timings.total_ms, outcome="error")
            logger.warning(
                events.STREAM_FAILED,
                extra={
                    "event": events.STREAM_FAILED,
                    "error_type": type(exc).__name__,
                    **timings.as_log_fields(),
                },
            )
            raise

        if guard.tripped:
            # The stream said something it should not have. Whatever already
            # went out cannot be recalled, so the safe text is appended rather
            # than substituted, and the rest of the answer is abandoned.
            metrics.increment("output_guard_replacements_total")
            logger.warning(
                "stream stopped by the output guard",
                extra={"event": "output_guard_tripped", "mode": "stream"},
            )
            yield "delta", "\n\n" + output_guard.SAFE_REPLACEMENT
            yield "citations", []
            yield "done", None
            return

        tail = guard.flush()
        if tail:
            yield "delta", tail

        timings.llm_total_ms = (time.perf_counter() - llm_started) * 1000
        _, resolved, final_confidence = self._finish(
            guard.text.strip(), decision, bundle, plan, confidence
        )
        timings.total_ms = (time.perf_counter() - started) * 1000

        metrics.increment("chat_success_total", mode="stream")
        metrics.observe("chat_duration", timings.total_ms, outcome="answered")
        metrics.observe("llm_duration", timings.llm_total_ms)
        self._log_completion(
            decision, bundle, plan, resolved, final_confidence, timings, None, "stream"
        )

        yield "citations", resolved.citations
        if resolved.related_pages:
            yield "related_pages", resolved.related_pages
        if resolved.suggested_questions:
            yield "suggestions", resolved.suggested_questions
        yield "done", None


__all__ = ["AssistantPipeline", "AssistantResult"]
