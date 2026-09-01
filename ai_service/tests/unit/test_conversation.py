"""Greetings, thanks and goodbyes: answered, never refused, never retrieved.

The bug this file exists to prevent: a visitor typed "hi" and was told what the
assistant could not help with. There was no conversational category at all, so a
greeting reached the classifier's last branch — no domain word, no recognised
shape — which is the definition of off topic.

Two properties are asserted throughout, and they are separate:

* the **intent** is conversational, so nothing is retrieved and no model is
  called;
* the **reply** is warm and does not contain a refusal, so the fix cannot be
  quietly undone by rewording the off-topic text into the conversational slot.
"""

from __future__ import annotations

import pytest

from app.api.schemas.chat import Message
from app.core.constants import Role
from app.query_router import QueryRouter
from app.query_router.conversation import collapse, detect, strip_leading_greeting
from app.query_router.intents import CONVERSATIONAL, Intent, Source

router = QueryRouter()


def route(question: str, history: list[Message] | None = None):
    return router.route(question, history)


# Phrases that would mean the fix had regressed into the old behaviour.
REFUSAL_TELLS = (
    "can't help",
    "cannot help",
    "couldn't find",
    "could not find",
    "not able to help",
    "i'm mainly here",
)


class TestGreetingsAreNotRefusals:
    """The reported bug, as a test."""

    @pytest.mark.parametrize(
        "question",
        [
            "hi",
            "Hi!",
            "hello",
            "HELLO",
            "hey",
            "hey there",
            "hii",
            "hiii",
            "hiiiii",
            "hlo",
            "helo",
            "yo",
            "howdy",
            "good morning",
            "Good Afternoon",
            "good evening",
            "greetings",
            "hey 👋",
            "  hello  ",
        ],
    )
    def test_a_greeting_is_a_greeting(self, question):
        assert route(question).intent is Intent.GREETING

    @pytest.mark.parametrize("question", ["hi", "hello", "good morning"])
    def test_a_greeting_is_answered_not_refused(self, question):
        text = route(question).reply.text.lower()
        for tell in REFUSAL_TELLS:
            assert tell not in text, f"{question!r} was answered with a refusal"

    def test_the_greeting_reply_offers_help(self):
        assert "help" in route("hi").reply.text.lower()

    def test_a_greeting_is_short(self):
        """One word in, one or two sentences back — not a brochure."""
        assert len(route("hi").reply.text) < 140


class TestOtherConversationalIntents:
    @pytest.mark.parametrize(
        ("question", "expected"),
        [
            ("how are you", Intent.SMALL_TALK),
            ("how are you?", Intent.SMALL_TALK),
            ("how's it going", Intent.SMALL_TALK),
            ("what's up", Intent.SMALL_TALK),
            ("sup", Intent.SMALL_TALK),
            ("nice to meet you", Intent.SMALL_TALK),
            ("ok", Intent.SMALL_TALK),
            ("okay", Intent.SMALL_TALK),
            ("cool", Intent.SMALL_TALK),
            ("nice", Intent.SMALL_TALK),
            ("who are you", Intent.HELP),
            ("who are you?", Intent.HELP),
            ("what can you do", Intent.HELP),
            ("what can you do?", Intent.HELP),
            ("how can you help me", Intent.HELP),
            ("what can i ask", Intent.HELP),
            ("thanks", Intent.THANKS),
            ("Thanks!", Intent.THANKS),
            ("thank you", Intent.THANKS),
            ("thank you so much", Intent.THANKS),
            ("thx", Intent.THANKS),
            ("cheers", Intent.THANKS),
            ("helpful", Intent.THANKS),
            ("that's helpful", Intent.THANKS),
            ("bye", Intent.GOODBYE),
            ("byee", Intent.GOODBYE),
            ("goodbye", Intent.GOODBYE),
            ("see you", Intent.GOODBYE),
            ("see you later", Intent.GOODBYE),
            ("take care", Intent.GOODBYE),
        ],
    )
    def test_intent(self, question, expected):
        assert route(question).intent is expected

    def test_who_are_you_gets_the_identity_answer(self):
        assert "ask zion" in route("who are you?").reply.text.lower()

    def test_what_can_you_do_describes_capabilities(self):
        text = route("what can you do?").reply.text.lower()
        assert "lift" in text and "website" in text

    def test_how_are_you_is_not_answered_as_an_engineering_question(self):
        """It used to match the explanation rule and run the whole pipeline."""
        decision = route("how are you?")
        assert decision.intent is Intent.SMALL_TALK
        assert decision.is_terminal


class TestNothingExpensiveRuns:
    """The fast path is the point: no embedding, no Qdrant, no rerank, no LLM."""

    @pytest.mark.parametrize(
        "question", ["hi", "hello", "how are you", "who are you", "thanks", "bye", "ok"]
    )
    def test_the_request_ends_at_the_router(self, question):
        assert route(question).is_terminal

    @pytest.mark.parametrize("question", ["hi", "thanks", "bye", "what can you do"])
    def test_no_source_is_consulted(self, question):
        plan = route(question).plan
        assert plan.sources == ()
        assert plan.skip_rag is True

    @pytest.mark.parametrize("question", ["hi", "thanks", "bye"])
    def test_retrieval_is_never_planned(self, question):
        assert Source.RAG not in route("hi").plan.sources

    def test_no_related_pages_are_attached(self):
        """A greeting is not a menu."""
        assert route("hi").plan.max_related_pages == 0

    @pytest.mark.parametrize("question", ["hi", "thanks", "bye"])
    def test_conversational_is_distinguished_from_refusal(self, question):
        """Both end at the router; only one is the assistant declining."""
        decision = route(question)
        assert decision.is_conversational is True
        assert decision.intent in CONVERSATIONAL

    def test_a_real_refusal_is_still_a_refusal(self):
        decision = route("who won the football match?")
        assert decision.intent is Intent.OFF_TOPIC
        assert decision.is_conversational is False


class TestRealQuestionsAreUntouched:
    """The greeting layer must not swallow anything that was actually asked."""

    @pytest.mark.parametrize(
        "question",
        [
            "hi, which lift suits a four-storey home?",
            "hello, what is an MRL lift?",
            "hey what capacity do I need",
            "good morning, does Zion offer maintenance contracts?",
            "thanks, but what about the pit depth?",
        ],
    )
    def test_a_greeting_in_front_of_a_question_is_still_a_question(self, question):
        decision = route(question)
        assert decision.intent not in CONVERSATIONAL
        assert not decision.is_terminal

    @pytest.mark.parametrize(
        ("question", "expected"),
        [
            ("what is MRL", Intent.GENERAL_LIFT_KNOWLEDGE),
            ("which lift for a villa", Intent.PRODUCT_INFORMATION),
            ("does Zion offer maintenance", Intent.COMPANY_KNOWLEDGE),
            ("bitcoin price", Intent.OFF_TOPIC),
        ],
    )
    def test_the_domain_table_still_holds(self, question, expected):
        assert route(question).intent is expected

    @pytest.mark.parametrize(
        "question",
        [
            # Words that contain a greeting but are not one.
            "high rise buildings",
            "hydraulic lift",
            "history of the company",
            "okay so what capacity does the hospital lift have",
            "how are your lifts maintained",
            "who are your suppliers",
        ],
    )
    def test_a_word_that_merely_contains_a_greeting_is_not_one(self, question):
        assert route(question).intent not in CONVERSATIONAL


class TestContextAwareness:
    """After a real exchange, a thank-you does not restart the introduction."""

    history = [
        Message(role=Role.USER, content="Which lift suits a four-storey home?"),
        Message(role=Role.ASSISTANT, content="A machine-room-less home elevator."),
    ]

    def test_thanks_is_brief_once_a_conversation_exists(self):
        opening = route("thanks").reply.text
        continuing = route("thanks", self.history).reply.text

        assert len(continuing) < len(opening)
        assert "you're welcome" in continuing.lower()

    def test_a_later_greeting_does_not_reintroduce_the_assistant(self):
        continuing = route("hi", self.history).reply.text
        assert "zion lifts, lift solutions" not in continuing.lower()

    def test_the_identity_answer_is_the_same_whenever_it_is_asked(self):
        """Asking who you are late deserves the same answer as asking early."""
        assert route("who are you?").reply.text == route("who are you?", self.history).reply.text


class TestNormalisationHelpers:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("hiii", "hii"), ("hiiiiii", "hii"), ("helloooo", "helloo"), ("hi", "hi")],
    )
    def test_elongation_is_collapsed(self, raw, expected):
        assert collapse(raw) == expected

    def test_collapsing_leaves_ordinary_words_alone(self):
        """No English word has a triple letter, so nothing real is damaged."""
        for word in ("lift", "hello", "installation", "committee"):
            assert collapse(word) == word

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("hi, what is an mrl", "what is an mrl"),
            ("hello what is an mrl", "what is an mrl"),
            ("good morning, does zion service lifts", "does zion service lifts"),
            ("what is an mrl", "what is an mrl"),
        ],
    )
    def test_a_leading_greeting_can_be_stripped_from_a_real_question(self, raw, expected):
        assert strip_leading_greeting(raw) == expected


class TestDetectorBoundaries:
    def test_an_empty_message_is_not_conversational(self):
        assert detect("") is None

    def test_a_long_message_is_never_a_greeting(self):
        """Whatever it opens with, a paragraph is a question."""
        assert detect("hello " + "lift capacity requirements " * 5) is None

    def test_detection_matches_the_whole_utterance_only(self):
        assert detect("hi") is not None
        assert detect("hi there") is not None
        assert detect("hi what is an mrl lift") is None
