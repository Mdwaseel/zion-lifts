"""Prompt template for conversational query rewriting."""

from __future__ import annotations

from app.api.schemas.chat import Message

REWRITE_SYSTEM = """You rewrite a follow-up question into a standalone search query.

Rules:
- Resolve every pronoun and ellipsis using the conversation.
- Keep the user's own terminology, entity names and constraints.
- Output ONLY the rewritten query. No preamble, no quotes, no explanation.
- If the question already stands alone, echo it back unchanged."""

REWRITE_TEMPLATE = """Conversation:
{history}

Follow-up question: {question}

Standalone query:"""


def build_rewrite_prompt(question: str, history: list[Message], max_turns: int = 6) -> str:
    recent = history[-max_turns:]
    rendered = "\n".join(f"{m.role.value.capitalize()}: {m.content}" for m in recent)
    return REWRITE_TEMPLATE.format(history=rendered or "(none)", question=question)
