"""Prompt templates for grounded answer generation."""

from __future__ import annotations

from app.prompts.system import system_prompt

RAG_SYSTEM = system_prompt(
    """Grounding rules:
- Use ONLY the numbered context passages provided. Treat them as the only truth.
- Cite every factual claim with the matching marker, e.g. [1] or [2][3].
- Place each citation immediately after the claim it supports, not at the end.
- If passages conflict, say so and cite both sides.
- If the context does not answer the question, reply exactly: INSUFFICIENT_CONTEXT
- Never cite a number that is not in the context below."""
)

RAG_TEMPLATE = """Context passages:
{context}

{history_block}Question: {question}

Answer the question using only the passages above, citing markers as you go."""

HISTORY_TEMPLATE = """Conversation so far:
{history}

"""


def build_rag_prompt(question: str, context: str, history: str | None = None) -> str:
    return RAG_TEMPLATE.format(
        context=context or "(no passages retrieved)",
        question=question,
        history_block=HISTORY_TEMPLATE.format(history=history) if history else "",
    )
