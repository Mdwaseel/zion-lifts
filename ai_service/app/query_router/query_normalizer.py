"""Prepare a question for matching without changing what it asks.

The distinction this module is built around: the string a *person* asked and the
string a *retriever* should be given are not the same, and conflating them is
how query rewriting goes wrong. Someone types "MRL lift for a villa"; the
lexical retriever will never match a document that spells it out as "machine
room less elevator", and a dense retriever only partly bridges the gap. But
replacing the question with the expansion loses "MRL" — which is what the
document might actually say — and rewriting it with a model costs a round trip
and can change the meaning outright.

So nothing is replaced. The original is preserved verbatim and carried through
to the model, and the retrieval query is the original *plus* the expansions that
apply, appended. Recall goes up, the question survives, and the transformation
is deterministic and inspectable — which the LLM rewrite in
:mod:`app.retrieval.query_rewriter` is not, and which is why that one still only
runs on follow-ups that need a pronoun resolved.

The vocabulary below is elevator-specific on purpose. A generic synonym list
would expand "drive" and "car" into their everyday meanings and make retrieval
worse; these are the terms this industry writes two ways.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

# Abbreviations, written out. Matched whole-word and case-insensitively, and
# expanded *alongside* the original rather than over it.
ABBREVIATIONS: Final[dict[str, str]] = {
    "mrl": "machine room less",
    "mr": "machine room",
    "amc": "annual maintenance contract",
    "vvvf": "variable voltage variable frequency drive",
    "ard": "automatic rescue device",
    "ups": "uninterruptible power supply",
    "ss": "stainless steel",
    "cop": "car operating panel",
    "lop": "landing operating panel",
    "vf": "variable frequency",
    "kg": "kilograms",
    "mps": "metres per second",
    "pwd": "persons with disabilities accessibility",
    "iot": "remote monitoring",
}

# Terms this industry writes two ways. Both forms are searched, because ingested
# documents and website copy do not agree with each other either.
SYNONYMS: Final[dict[str, tuple[str, ...]]] = {
    "elevator": ("lift",),
    "elevators": ("lifts",),
    "lift": ("elevator",),
    "lifts": ("elevators",),
    "home lift": ("residential lift", "villa lift", "domestic elevator"),
    "home elevator": ("residential lift", "home lift"),
    "villa lift": ("home lift", "residential lift"),
    "residential lift": ("home lift", "villa lift"),
    "goods lift": ("freight elevator", "service lift"),
    "freight lift": ("goods lift", "freight elevator"),
    "service lift": ("goods lift", "dumbwaiter"),
    "dumbwaiter": ("service lift", "dumb waiter"),
    "hospital lift": ("stretcher lift", "bed elevator"),
    "capsule lift": ("panoramic lift", "observation elevator"),
    "passenger lift": ("passenger elevator",),
    "traction": ("gearless traction", "rope"),
    "hydraulic": ("hydraulic drive", "piston"),
    "maintenance": ("servicing", "amc", "annual maintenance contract"),
    "installation": ("install", "erection", "commissioning"),
    "capacity": ("load", "rated load", "persons"),
    "speed": ("velocity", "m/s"),
    "shaft": ("hoistway", "well"),
    "pit": ("pit depth",),
    "headroom": ("overhead", "top clearance"),
    "counterweight": ("counter weight", "balance weight"),
    "levelling": ("leveling", "floor levelling", "stopping accuracy"),
    "quotation": ("quote", "pricing", "estimate"),
    "quote": ("quotation", "pricing"),
}

# Misspellings common enough to be worth correcting, and unambiguous enough to
# be safe to. Corrected in the retrieval query only — the visitor's own words
# are never edited on screen.
TYPOS: Final[dict[str, str]] = {
    "elavator": "elevator",
    "elevater": "elevator",
    "elevatore": "elevator",
    "elivator": "elevator",
    "escalater": "escalator",
    "hydrolic": "hydraulic",
    "hydralic": "hydraulic",
    "hydraulinc": "hydraulic",
    "tracton": "traction",
    "tractoin": "traction",
    "counterweigth": "counterweight",
    "mantainance": "maintenance",
    "maintainance": "maintenance",
    "maintenence": "maintenance",
    "instalation": "installation",
    "capasity": "capacity",
    "residencial": "residential",
    "hospitl": "hospital",
    "machineroom": "machine room",
    "dumbwaitor": "dumbwaiter",
}

# The company, however it is written. Detecting it is what separates "what is an
# MRL lift" from "does Zion do MRL lifts", so the list is generous.
COMPANY_TERMS: Final[tuple[str, ...]] = (
    "zion",
    "zion lifts",
    "zion lift",
    "zionlifts",
    "your company",
    "your firm",
    "you guys",
)

# Product families the site sells. Extracted as entities so the orchestrator can
# tell a catalogue question from an engineering one.
PRODUCT_TERMS: Final[tuple[str, ...]] = (
    "passenger lift",
    "passenger elevator",
    "home lift",
    "home elevator",
    "villa lift",
    "residential lift",
    "hospital lift",
    "stretcher lift",
    "goods lift",
    "freight lift",
    "service lift",
    "dumbwaiter",
    "dumb waiter",
    "capsule lift",
    "panoramic lift",
    "observation lift",
    "car stacker",
    "car parking lift",
    "escalator",
    "travelator",
    "platform lift",
    "wheelchair lift",
    "mrl",
    "machine room less",
    "traction lift",
    "hydraulic lift",
)

_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_FLOORS = re.compile(
    r"\b(\d{1,3})\s*[- ]?\s*(?:floors?|storey?s?|stories|stops?|levels?|g\+\d+)\b",
    re.IGNORECASE,
)
_PERSONS = re.compile(r"\b(\d{1,3})\s*[- ]?\s*(?:persons?|people|passengers?|pax)\b", re.IGNORECASE)
_WEIGHT = re.compile(r"\b(\d{2,5})\s*(?:kg|kgs|kilograms?)\b", re.IGNORECASE)

# How many expansion terms may be appended. Past this the retrieval query stops
# describing the question and starts describing the vocabulary — every extra
# term dilutes the lexical scoring of the ones that mattered.
MAX_EXPANSIONS: Final = 8


@dataclass(slots=True, frozen=True)
class Entities:
    """What the question named, as far as it can be told without a model."""

    mentions_company: bool = False
    products: tuple[str, ...] = field(default_factory=tuple)
    floors: int | None = None
    persons: int | None = None
    weight_kg: int | None = None

    @property
    def is_empty(self) -> bool:
        return not (self.mentions_company or self.products or self.floors or self.persons)


@dataclass(slots=True, frozen=True)
class NormalizedQuery:
    """One question, in the several forms the pipeline needs it in."""

    #: Exactly what the visitor typed, after unicode normalisation. Never edited.
    original: str
    #: Lower-cased and punctuation-light. For pattern matching only.
    matchable: str
    #: What retrieval should search for: the original plus expansions.
    retrieval: str
    entities: Entities = field(default_factory=Entities)
    expansions: tuple[str, ...] = field(default_factory=tuple)
    corrections: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def word_count(self) -> int:
        return len(_WORD.findall(self.matchable))


def _matchable(text: str) -> str:
    """Lower case, with punctuation reduced to spaces.

    Apostrophes survive inside words so "what's" stays one token; everything
    else becomes a separator, which keeps "MRL-lift" and "MRL lift" identical.
    """
    lowered = text.lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']|_", " ", lowered)).strip()


def _phrases(matchable: str, candidates: tuple[str, ...]) -> tuple[str, ...]:
    """Which of ``candidates`` appear as whole phrases.

    A trailing "s" is allowed on the last word, because the visitor writes
    "passenger lifts" and the catalogue says "passenger lift". Anything more
    than that — stemming, fuzzy matching — would start matching phrases nobody
    typed, and the cost of a wrong entity here is a wrongly routed question.
    """
    found = []
    for phrase in candidates:
        if re.search(rf"(?<!\w){re.escape(phrase)}s?(?!\w)", matchable):
            found.append(phrase)
    return tuple(found)


def extract_entities(matchable: str) -> Entities:
    """Names and numbers, pulled out without a model call.

    Deliberately shallow. The point is not to understand the question but to
    answer three questions cheaply: did they name the company, did they name a
    product family, and did they give a building size — which together decide
    whether a "which lift is best?" is ambiguous or already answered.
    """
    products = _phrases(matchable, PRODUCT_TERMS)
    # Keep the most specific of any overlapping pair: "home lift" beats "lift",
    # and reporting both would make a specific question look vague.
    products = tuple(p for p in products if not any(p != o and p in o for o in products))

    floors = _FLOORS.search(matchable)
    persons = _PERSONS.search(matchable)
    weight = _WEIGHT.search(matchable)

    def as_int(match: re.Match[str] | None) -> int | None:
        if match is None:
            return None
        try:
            return int(match.group(1))
        except (ValueError, IndexError):  # pragma: no cover - regex guarantees digits
            return None

    return Entities(
        mentions_company=bool(_phrases(matchable, COMPANY_TERMS)),
        products=products,
        floors=as_int(floors),
        persons=as_int(persons),
        weight_kg=as_int(weight),
    )


def normalize(question: str) -> NormalizedQuery:
    """Produce every form of the question the pipeline needs.

    The original is returned untouched. Everything else is derived, and the
    derivations are additive: a term is expanded, never replaced, so a document
    that uses the visitor's own wording still ranks.
    """
    matchable = _matchable(question)
    words = _WORD.findall(matchable)

    corrections: list[tuple[str, str]] = []
    corrected_words: list[str] = []
    for word in words:
        fixed = TYPOS.get(word)
        if fixed:
            corrections.append((word, fixed))
            corrected_words.append(fixed)
        else:
            corrected_words.append(word)
    corrected = " ".join(corrected_words)

    expansions: list[str] = []

    def add(term: str) -> None:
        if term and term not in expansions and term not in corrected:
            expansions.append(term)

    for word in dict.fromkeys(corrected_words):
        written_out = ABBREVIATIONS.get(word)
        if written_out:
            add(written_out)

    for phrase, alternatives in SYNONYMS.items():
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", corrected):
            for alternative in alternatives:
                add(alternative)

    expansions = expansions[:MAX_EXPANSIONS]

    # The visitor's own sentence first, so its term order still drives ranking;
    # the expansions trail it as extra vocabulary rather than as a rewrite.
    retrieval = question if not expansions else f"{question} {' '.join(expansions)}"

    return NormalizedQuery(
        original=question,
        matchable=corrected,
        retrieval=retrieval,
        entities=extract_entities(corrected),
        expansions=tuple(expansions),
        corrections=tuple(corrections),
    )


__all__ = [
    "ABBREVIATIONS",
    "COMPANY_TERMS",
    "MAX_EXPANSIONS",
    "PRODUCT_TERMS",
    "SYNONYMS",
    "TYPOS",
    "Entities",
    "NormalizedQuery",
    "extract_entities",
    "normalize",
]
