"""Greetings, thanks and goodbyes — answered without asking anything.

Somebody typing "hi" is not asking a question. They are opening a conversation,
and the only correct response is to open one back. Before this module existed
the router had no category for that, so "hi" fell through every domain rule to
the last branch — no domain word, no recognised shape — and was answered with a
refusal explaining what the assistant could not help with. "how are you?" was
worse: it matched the *explanation request* rule, so it went through embedding,
vector search, reranking and an LLM call before answering a pleasantry as though
it were an engineering question.

Both are fixed here, and fixed cheaply. Detection is a set of whole-utterance
patterns over the already-normalised text; a match ends the request with written
text. No embedding, no Qdrant, no reranking, no confidence gate, no model.

**Whole-utterance matching is the load-bearing decision.** Every pattern is
anchored at both ends, so a greeting is only a greeting when it is the entire
message. "hi" is conversational; "hi, which lift suits a four-storey home?" is a
lift question with a greeting attached, and it routes to the catalogue like any
other. Prefix matching would have swallowed the question after the comma, which
is a far worse failure than the one being fixed.

It is also what keeps this safe to run early: there is no payload that both
matches "^h+e+l+l+o+$" and carries an instruction. Security still runs first
regardless — see :class:`~app.query_router.QueryRouter.route` — because that
check costs microseconds and defence in depth is cheaper than being clever.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from app.query_router.intents import Intent

# --- normalisation -----------------------------------------------------------

# Elongation is how people type warmth: "hiii", "helloo", "thankss". Collapsing
# a run of three or more identical letters to two leaves real words alone
# (nothing in English has a triple letter) and turns every elongated greeting
# into one the patterns below already know.
_ELONGATED: Final = re.compile(r"(.)\1{2,}")

# Politeness that wraps a real question — "hi, what is an MRL?" — is stripped
# only for the purpose of *classifying the remainder*, never from the question
# that gets answered. See `strip_leading_greeting`.
_LEADING_GREETING: Final = re.compile(
    r"^(?:hi+|hey+|hello+|hlo+|helo+|yo|good\s+(?:morning|afternoon|evening|day))"
    r"[\s,.!]+(?=\S)"
)


def collapse(text: str) -> str:
    """The form the patterns match against: elongation flattened, spaces tidy."""
    return _ELONGATED.sub(r"\1\1", " ".join(text.split()))


def strip_leading_greeting(matchable: str) -> str:
    """ "hi, what is an MRL?" -> "what is an MRL?".

    Used only to decide what the *rest* of the message is about. A greeting in
    front of a real question must not make the question disappear, and it must
    not make the greeting win either.
    """
    return _LEADING_GREETING.sub("", matchable, count=1).strip()


# --- the rules ---------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class ConversationalReply:
    """A written answer to a conversational message."""

    intent: Intent
    text: str
    #: Names which rule fired, for logs and metrics. Never the message itself.
    signal: str


def _pattern(body: str) -> re.Pattern[str]:
    """Anchored at both ends: a rule fires only on the whole utterance."""
    return re.compile(rf"^(?:{body})$")


# Optional politeness that may wrap any of these without changing what they are.
_PLEASE = r"(?:\s*please)?"
_THERE = r"(?:\s+(?:there|everyone|team|guys))?"

# (intent, pattern, reply key, signal). Order matters only where two rules could
# both match; the first wins, so the more specific ones come first.
_RULES: Final[tuple[tuple[Intent, re.Pattern[str], str, str], ...]] = (
    # --- HELP: who and what. Before SMALL_TALK, because "who are you" would
    # otherwise read as pleasantry when it is really a capability question.
    (
        Intent.HELP,
        _pattern(r"(?:so\s+)?who(?:'s| is| are)\s+(?:you|u|this|ask zion)\??"),
        "identity",
        "identity_question",
    ),
    (
        Intent.HELP,
        _pattern(
            r"(?:what|how)\s+(?:can|could|do|does|should)\s+"
            r"(?:you|u|i|this|it)\s+(?:do|help|assist|ask|know)"
            r"(?:\s+(?:me|with|about))?(?:\s+\w+)*\??"
        ),
        "capability",
        "capability_question",
    ),
    (
        Intent.HELP,
        _pattern(r"(?:help|what are your capabilities|what do you know)\??"),
        "capability",
        "help_request",
    ),
    # --- GREETING
    (
        Intent.GREETING,
        _pattern(rf"(?:hi+|hey+|hello+|helo+|hlo+|hii+|yo|heya+|howdy){_THERE}"),
        "greeting",
        "greeting_word",
    ),
    (
        Intent.GREETING,
        _pattern(r"(?:good\s+(?:morning|afternoon|evening|day))" + _THERE),
        "greeting",
        "time_of_day_greeting",
    ),
    (
        Intent.GREETING,
        _pattern(r"(?:greetings|namaste|salaam|hi+\s+hi+)"),
        "greeting",
        "greeting_word",
    ),
    # --- SMALL_TALK
    (
        Intent.SMALL_TALK,
        _pattern(r"how(?:'s| is| are)\s+(?:you|u|it going|things|everything)(?:\s+doing)?\??"),
        "how_are_you",
        "how_are_you",
    ),
    (
        Intent.SMALL_TALK,
        _pattern(r"(?:what'?s|whats|wat)\s+up\??|sup\??|wassup\??"),
        "whats_up",
        "whats_up",
    ),
    (
        Intent.SMALL_TALK,
        _pattern(r"(?:nice|good|pleased|great)\s+to\s+(?:meet|see)\s+(?:you|u)\??"),
        "nice_to_meet",
        "nice_to_meet",
    ),
    (
        Intent.SMALL_TALK,
        _pattern(r"(?:ok|okay|oki|k|kk|alright|cool|nice|great|awesome|good|fine|sure|got it)"),
        "acknowledged",
        "acknowledgement",
    ),
    # --- THANKS
    (
        Intent.THANKS,
        _pattern(
            rf"(?:thanks?|thank\s+(?:you|u)|thanx|thnx|thx|tks|ty|tysm|cheers|much appreciated"
            rf"|appreciate\s+(?:it|that)){_PLEASE}"
            rf"(?:\s+(?:so\s+much|a\s+lot|very\s+much|mate|buddy))?"
        ),
        "thanks",
        "thanks",
    ),
    (
        Intent.THANKS,
        _pattern(r"(?:that(?:'s| is)\s+)?(?:very\s+)?(?:helpful|useful|perfect|brilliant)"),
        "thanks",
        "praise",
    ),
    # --- GOODBYE
    (
        Intent.GOODBYE,
        _pattern(
            r"(?:bye+|goodbye+|good\s+bye|see\s+(?:you|ya|u)(?:\s+(?:later|soon))?"
            r"|catch\s+you\s+later|take\s+care|cya|later|farewell"
            r"|good\s+night|gn)"
        ),
        "goodbye",
        "goodbye",
    ),
)


# --- replies -----------------------------------------------------------------
#
# Written, not generated. Short, because the visitor said one word and a
# paragraph back is not a conversation. Two forms of most: the `opening` one
# introduces what the assistant is good for, and the `continuing` one does not —
# after four exchanges about hospital lifts, answering "thanks" by re-explaining
# what Ask Zion is reads as though nothing before it was heard.

_OPENING: Final[dict[str, str]] = {
    "greeting": "Hi! 👋 How can I help? You can ask me about Zion Lifts, lift solutions, "
    "or elevator technology.",
    "how_are_you": "I'm doing well, thanks! How can I help you with lifts or elevators today?",
    "whats_up": "All good here! What can I help you with — lifts, installation, or service?",
    "nice_to_meet": "Nice to meet you too! What would you like to know about lifts?",
    "acknowledged": "Anything else I can help you with?",
    "identity": "I'm Ask Zion, Zion Lifts' AI assistant. I can help with our lift solutions, "
    "services, and general elevator technology.",
    "capability": "I can help you explore Zion's lift solutions and services, answer general "
    "questions about elevators and lift technology, and guide you to relevant "
    "sections of the website.",
    "thanks": "You're welcome! 😊 Feel free to ask if you have any other questions.",
    "goodbye": "Goodbye! 👋 Feel free to come back anytime you need help with lift solutions "
    "or elevator technology.",
}

_CONTINUING: Final[dict[str, str]] = {
    "greeting": "Hi again! 👋 What would you like to know?",
    "how_are_you": "Doing well, thanks! What else can I help you with?",
    "whats_up": "All good! What else can I help with?",
    "nice_to_meet": "Likewise! What else would you like to know?",
    "acknowledged": "Anything else?",
    "thanks": "You're welcome! 😊",
    "goodbye": "Goodbye! 👋 Come back any time.",
    # identity and capability are the same answer whenever they are asked: the
    # visitor wants the description, not a shorter one because they asked late.
}


def detect(matchable: str, *, has_history: bool = False) -> ConversationalReply | None:
    """The conversational reply for this message, or None if it is a real query.

    ``matchable`` is :attr:`NormalizedQuery.matchable` — lower-cased with
    punctuation and emoji already reduced to spaces, so "Hi!", "HELLO" and
    "hey 👋" all arrive here as bare words.
    """
    text = collapse(matchable)
    if not text or len(text) > 60:
        # A long message is a question, whatever it opens with. The cap stops a
        # pathological input from being walked by a dozen regexes, and nothing
        # conversational is anywhere near it.
        return None

    for intent, pattern, key, signal in _RULES:
        if pattern.match(text):
            replies = _CONTINUING if has_history else _OPENING
            return ConversationalReply(
                intent=intent,
                text=replies.get(key) or _OPENING[key],
                signal=signal,
            )
    return None


__all__ = [
    "ConversationalReply",
    "collapse",
    "detect",
    "strip_leading_greeting",
]
